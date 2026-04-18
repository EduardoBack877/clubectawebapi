from fastapi import UploadFile, File, Form
from fastapi.responses import Response
from fastapi import APIRouter, Depends, HTTPException
import base64
from typing import Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
import database_controller
import jwt_utils

router = APIRouter()


@router.post("/insert/admin/novo-ambiente")
async def criar_ambiente(
        nome: str = Form(...),
        descricao: str = Form(...),
        capacidade: int = Form(0),
        ativo: int = Form(1),
        img: Optional[UploadFile] = File(None),
        db: Session = Depends(database_controller.get_db)
):
    try:
        capa_dados = None
        capa_mimetype = None
        capa_nome = None

        # 📸 lê imagem
        if img:
            print("📸 veio imagem:", img.filename)
            capa_dados = await img.read()  # 🔥 vira bytes (bytea)
            capa_mimetype = img.content_type
            capa_nome = img.filename
        else:
            print("nao veio foto")
        # 🧠 INSERT no banco

        result = db.execute(
            text("""
                INSERT INTO ambiente (
                    ambientes_uid,
                    nome,
                    descricao,
                    capacidade,
                    isactive,
                    capa_dados,
                    capa_mimetype,
                    capa_nome,
                    createuserid
                )
                VALUES (
                    uuid_generate_v4(),
                    :nome, :descricao, :capacidade, :ativo,
                    :capa_dados, :capa_mimetype, :capa_nome, :user
                )
                RETURNING ambientes_uid, nome, descricao, capacidade, isactive;
            """),
            {
                "nome": nome,
                "descricao": descricao,
                "capacidade": capacidade,
                "ativo": ativo,
                "capa_dados": capa_dados,
                "capa_mimetype": capa_mimetype,
                "capa_nome": capa_nome,
                "user": 1
            }
        )

        row = result.fetchone()
        db.commit()

        return {
            "id": str(row[0]),
            "nome": row[1],
            "descricao": row[2],
            "capacidade": row[3],
            "ativo": bool(row[4]),
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar ambiente: {str(e)}")


# ── EDITAR AMBIENTE ─────────────────────────────────────────────
@router.put("/update/admin/ambiente/{ambientes_uid}")
async def editar_ambiente(
        ambientes_uid: str,
        nome: str = Form(...),
        descricao: str = Form(...),
        capacidade: int = Form(0),
        ativo: int = Form(1),
        img: Optional[UploadFile] = File(None),
        db: Session = Depends(database_controller.get_db),
):
    try:
        params = {
            "nome": nome,
            "descricao": descricao,
            "capacidade": capacidade,
            "ativo": ativo,
            "uid": ambientes_uid,
        }

        capa_clause = ""
        if img:
            params["capa_dados"] = await img.read()
            params["capa_mimetype"] = img.content_type
            params["capa_nome"] = img.filename
            capa_clause = ", capa_dados=:capa_dados, capa_mimetype=:capa_mimetype, capa_nome=:capa_nome"

        result = db.execute(text(f"""
            UPDATE ambiente
            SET nome=:nome,
                descricao=:descricao,
                capacidade=:capacidade,
                isactive=:ativo
                {capa_clause}
            WHERE ambientes_uid=:uid
            RETURNING ambientes_uid, nome, descricao, capacidade, isactive
        """), params)

        db.commit()
        row = result.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Ambiente não encontrado")

        return {
            "id": str(row[0]),
            "nome": row[1],
            "descricao": row[2],
            "capacidade": row[3],
            "ativo": bool(row[4]),
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao editar ambiente: {str(e)}")


# ── DELETAR AMBIENTE ────────────────────────────────────────────
@router.delete("/delete/admin/ambiente/{ambientes_uid}")
def deletar_ambiente(
    ambientes_uid: str,
    db: Session = Depends(database_controller.get_db),
):
    print(f"Tentando deletar ambiente: {ambientes_uid}")
    try:
        # 1. Limpa a galeria (As chaves devem ser IGUAIS: :uid -> "uid")
        db.execute(
            text("DELETE FROM ambiente_galeria WHERE ambientes_uid = :uid"),
            {"uid": ambientes_uid}
        )

        # 2. Deleta o ambiente
        result = db.execute(
            text("DELETE FROM ambiente WHERE ambientes_uid = :uid RETURNING ambientes_uid"),
            {"uid": ambientes_uid}
        )

        deleted_id = result.fetchone()

        if not deleted_id:
            # Se cair aqui, o ID enviado não existe no banco
            print("Nenhum ambiente encontrado com esse ID")
            raise HTTPException(status_code=404, detail="Ambiente não encontrado")

        db.commit()
        print(f"Sucesso! Deletado: {deleted_id[0]}")
        return {"status": "success", "deleted_id": deleted_id[0]}

    except Exception as e:
        db.rollback()
        print(f"Erro capturado: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao deletar: {str(e)}")


# ── LISTAR AMBIENTES ────────────────────────────────────────────
@router.get("/api/ambientes")
def listar_ambientes(user_data: dict = Depends(jwt_utils.validate_token),  db: Session = Depends(database_controller.get_db)):
    try:
        # Adicionei todas as colunas no GROUP BY para evitar erro de sintaxe SQL
        # E troquei a.createdate por a.ambientes_uid caso a coluna createdate não exista
        query = text("""
            SELECT
                a.ambientes_uid, 
                a.nome, 
                a.descricao, 
                a.capacidade, 
                a.isactive,
                a.capa_mimetype, 
                a.capa_nome,
                COUNT(DISTINCT g.ambiente_galeria_uid) AS total_fotos,
                COUNT(DISTINCT r.reservas_uid) AS total_reservas_ativas
            FROM ambiente a
            LEFT JOIN ambiente_galeria g ON g.ambientes_uid = a.ambientes_uid
            LEFT JOIN reservas r ON r.ambientes_uid = a.ambientes_uid 
                AND r.isactive = 1 AND r.data_reserva >= CURRENT_DATE
            WHERE a.isactive = 1 
            GROUP BY 
                a.ambientes_uid, a.nome, a.descricao, a.capacidade, 
                a.isactive, a.capa_mimetype, a.capa_nome
            ORDER BY a.ambientes_uid DESC
        """)

        result = db.execute(query)
        rows = result.fetchall()

        return [
            {
                "id": str(r[0]),
                "nome": r[1],
                "descricao": r[2],
                "capacidade": r[3],
                "ativo": bool(r[4]),
                "capa_url": f"/ambientes/{r[0]}/capa" if r[5] else None,
                "capa_nome": r[6],
                "total_fotos": r[7],
                "quantidade_reservas": r[8]
            }
            for r in rows
        ]

    except Exception as e:
        # ESTE PRINT É ESSENCIAL: Ele vai mostrar o erro real no seu terminal do VS Code
        print(f"ERRO NO BACKEND: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar: {str(e)}")


# ── CAPA DO AMBIENTE ────────────────────────────────────────────
@router.get("/{ambientes_uid}/capa")
def get_capa(ambientes_uid: str, db: Session = Depends(database_controller.get_db)):
    try:
        row = db.execute(text("""
            SELECT capa_dados, capa_mimetype
            FROM ambientes
            WHERE ambientes_uid=:uid
        """), {"uid": ambientes_uid}).fetchone()

        if not row or not row[0]:
            raise HTTPException(status_code=404, detail="Capa não encontrada")

        return Response(content=bytes(row[0]), media_type=row[1])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar capa: {str(e)}")


# ── LISTAR RESERVAS ──────────────────────────────────────────────
@router.get("/get/admin/ambiente/{ambientes_uid}/reservas")
def get_reservas(ambientes_uid: str, db=Depends(database_controller.get_db)):
    try:
        print("chegou na rota")
        sql = text("""
            SELECT 
                r.reservas_uid,
                r.data_reserva,
                r.hora_inicio,
                r.hora_fim,
                r.status,
                r.usuarioid,
                u.nome,
                u.document,
                u.telefone
            FROM RESERVAS r
            JOIN usuario u ON u.id = r.usuarioid
            WHERE r.ambientes_uid = :ambiente_uid 
              AND r.isactive = 1
              AND r.data_reserva >= CURRENT_DATE
            ORDER BY r.data_reserva ASC, r.hora_inicio ASC;
        """)

        # Recomendo usar .mappings() para não se perder nos índices [0], [1]...
        result = db.execute(sql, {"ambiente_uid": ambientes_uid}).mappings().all()

        print(f"Encontrados {len(result)} resultados")

        return [
            {
                "reservas_uid": str(r["reservas_uid"]),
                "data_reserva": str(r["data_reserva"]),
                "hora_inicio": str(r["hora_inicio"])[:5],
                "hora_fim": str(r["hora_fim"])[:5],
                "status": r["status"],
                "nomeUsuario": r["nome"],
                "documento": r["document"] or "",
                "telefone": r["telefone"] or ""
            }
            for r in result
        ]

    except Exception as e:
        print(f"Erro ao buscar reservas: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar reservas.")



# ── LISTAR GALERIA ──────────────────────────────────────────────
@router.get("/{ambientes_uid}/galeria")
def listar_galeria(ambientes_uid: str, db: Session = Depends(database_controller.get_db)):
    try:
        rows = db.execute(text("""
            SELECT ambiente_galeria_uid, foto_nome, foto_mimetype,
                   foto_tamanho, legenda, ordem
            FROM ambiente_galeria
            WHERE ambientes_uid = :uid
            ORDER BY ordem ASC
        """), {"uid": ambientes_uid}).fetchall()

        return [
            {
                "id": str(r[0]),
                "foto_nome": r[1],
                "legenda": r[4],
                "ordem": r[5],
                "url": f"/ambientes/{ambientes_uid}/galeria/{r[0]}/imagem",
            }
            for r in rows
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar galeria: {str(e)}")


# ── BUSCAR FOTO ─────────────────────────────────────────────────
@router.get("/{ambientes_uid}/galeria/{foto_uid}/imagem")
def get_foto(ambientes_uid: str, foto_uid: str, db: Session = Depends(database_controller.get_db)):
    try:
        row = db.execute(text("""
            SELECT foto_dados, foto_mimetype
            FROM ambiente_galeria
            WHERE ambiente_galeria_uid=:foto_uid
              AND ambientes_uid=:amb_uid
        """), {"foto_uid": foto_uid, "amb_uid": ambientes_uid}).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Foto não encontrada")

        return Response(content=bytes(row[0]), media_type=row[1])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar foto: {str(e)}")


# Parte de album de ambiente, serve para adicionar, listar e remover imagens
@router.get("/get/ambiente/album/{ambientes_uid}")
def get_ambiente_album(ambientes_uid: str, db: Session = Depends(database_controller.get_db)):
    try:
        # SQL com a ordem exata para facilitar o mapeamento
        sql = text("""
            SELECT 
                ambiente_galeria_uid, 
                foto_nome, 
                foto_mimetype, 
                foto_tamanho, 
                legenda, 
                ordem,
                foto_dados
            FROM ambiente_galeria 
            WHERE ambientes_uid = :ambientes_uid
            ORDER BY ordem ASC
        """)

        result = db.execute(sql, {"ambientes_uid": ambientes_uid}).fetchall()

        album = []
        for r in result:
            # r[0]: uid, r[1]: nome, r[2]: mimetype, r[3]: tamanho, r[4]: legenda, r[5]: ordem, r[6]: dados

            # Monta o Data URI para pré-visualização no Admin
            foto_base64 = ""
            if r[6]:  # Se houver dados binários
                foto_base64 = f"data:{r[2]};base64,{base64.b64encode(r[6]).decode('utf-8')}"

            album.append({
                "id": str(r[0]),
                "foto_nome": r[1] or "sem_nome.png",
                "foto_mimetype": r[2] or "image/png",
                "foto_tamanho": r[3] or 0,
                "legenda": r[4] or "",
                "ordem": r[5] or 0,
                "foto_url": foto_base64  # No Admin, isso alimenta o <img src={...} />
            })

        return album

    except Exception as e:
        print(f"Erro detalhado: {e}")  # Log para debug no terminal
        raise HTTPException(status_code=500, detail="Erro ao carregar álbum do ambiente")


# Insere no album a imagem
@router.post("/api/ambientes/{ambientes_uid}/galeria")
async def adicionar_foto(
        ambientes_uid: str,
        foto: UploadFile = File(...),
        legenda: str = Form(None),
        ordem: int = Form(0),
        db: Session = Depends(database_controller.get_db),
):
    try:
        foto_bytes = await foto.read()

        # INSERT (Certifique-se de que a tabela existe no banco)
        result = db.execute(text("""
            INSERT INTO ambiente_galeria (
                ambientes_uid, foto_dados, foto_mimetype,
                foto_nome, foto_tamanho, legenda, ordem
            )
            VALUES (:ambientes_uid, :foto_dados, :foto_mimetype,
                    :foto_nome, :foto_tamanho, :legenda, :ordem)
            RETURNING ambiente_galeria_uid
        """), {
            "ambientes_uid": ambientes_uid,
            "foto_dados": foto_bytes,
            "foto_mimetype": foto.content_type,
            "foto_nome": foto.filename,
            "foto_tamanho": len(foto_bytes),
            "legenda": legenda,
            "ordem": ordem,
        })
        db.commit()
        return {"id": str(result.fetchone()[0])}
    except Exception as e:
        db.rollback()
        print(f"Erro no insert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Rota para deletar a imagem do album
@router.delete("/api/admin/ambiente/album/delete/{ambientes_uid}/{foto_uid}")
def delete_ambiente_imagem(
        ambientes_uid: str, foto_uid: str, db: Session = Depends(database_controller.get_db)):
    try:
        result = db.execute(text("""
            DELETE FROM ambiente_galeria
            WHERE ambiente_galeria_uid=:foto_uid
              AND ambientes_uid=:amb_uid
            RETURNING ambiente_galeria_uid
        """), {"foto_uid": foto_uid, "amb_uid": ambientes_uid})

        db.commit()

        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Foto não encontrada")

        return {"deleted": foto_uid}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao deletar foto: {str(e)}")
        print("🔥 ERRO BACKEND:", e)
        return {"erro": str(e)}


# ── EDITAR AMBIENTE ─────────────────────────────────────────────
@router.put("/update/admin/reserva/{reserva_uid}")
async def editar_reserva(
    reserva_uid: str,
    data_reserva: str = Form(...),    # Nome ajustado para clareza
    hora_inicio: str = Form(...),     # Nome ajustado
    hora_fim: str = Form(...),        # Nome ajustado
    status: str = Form(...),
    db: Session = Depends(database_controller.get_db),
):
    try:
        params = {
            "uid": reserva_uid,
            "d": data_reserva,
            "hi": hora_inicio,
            "hf": hora_fim,
            "st": status,
        }

        query = text("""
            UPDATE reservas
            SET
                data_reserva = :d,
                hora_inicio = :hi,
                hora_fim = :hf,
                status = :st,
                changedate = NOW()
            WHERE reservas_uid = :uid
            RETURNING reservas_uid, data_reserva, hora_inicio, hora_fim, status
        """)

        result = db.execute(query, params)
        row = result.fetchone()

        if not row:
            db.rollback()
            raise HTTPException(status_code=404, detail="Reserva não encontrada")

        db.commit()

        return {
            "id": str(row[0]),
            "data_reserva": str(row[1]),
            "hora_inicio": str(row[2])[:5], # Formata para HH:mm
            "hora_fim": str(row[3])[:5],    # Formata para HH:mm
            "status": row[4],               # Retorna a string ('confirmada', etc)
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Erro ao editar reserva: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@router.put("/update/admin/inativar/reserva/{reserva_uid}") # Aqui está no SINGULAR
def inativar_reserva(
        reserva_uid: str, # Mude de 'reservas_uid' para 'reserva_uid' para bater com a rota acima
        db: Session = Depends(database_controller.get_db),
):
    try:
        query = text("""
            UPDATE reservas
            SET isactive = 0
            WHERE reservas_uid = :uid
            RETURNING reservas_uid, isactive
        """)

        # Use o nome da variável que você definiu no argumento acima
        result = db.execute(query, {"uid": reserva_uid})
        row = result.fetchone()

        if not row:
            # Importante: rollback se não encontrar ninguém
            db.rollback()
            raise HTTPException(status_code=404, detail="Reserva não encontrada")

        db.commit()

        return {
            "reserva_uid": str(row[0]),
            "isactive": row[1],
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Erro ao inativar reserva: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


# ── LISTAR EVENTOS ─────────────────────────────────────────────────────────────
@router.get("/api/eventos")
def listar_eventos(
        user_data: dict = Depends(jwt_utils.validate_token),  # ← token obrigatório
        db: Session = Depends(database_controller.get_db)
):
    try:
        query = text("""
            SELECT
                e.evento_uid,
                e.nome,
                e.descricao,
                e.data,
                e.isactive,
                COUNT(DISTINCT g.evento_galeria_uid) AS total_fotos
            FROM evento e
            LEFT JOIN evento_galeria g
                ON g.evento_uid = e.evento_uid AND g.isactive = 1
            WHERE e.isactive = 1
            GROUP BY e.evento_uid, e.nome, e.descricao, e.data, e.isactive
            ORDER BY e.data DESC
        """)

        rows = db.execute(query).fetchall()

        return [
            {
                "id": str(r[0]),
                "nome": r[1],
                "descricao": r[2],
                "data": str(r[3]),
                "ativo": bool(r[4]),
                "total_fotos": r[5],
            }
            for r in rows
        ]

    except Exception as e:
        print(f"ERRO ao listar eventos: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar eventos: {str(e)}")


# ── CRIAR EVENTO ───────────────────────────────────────────────────────────────
@router.post("/insert/admin/novo-evento")
async def criar_evento(
        nome: str = Form(...),
        descricao: str = Form(...),
        data: str = Form(...),
        user_data: dict = Depends(jwt_utils.validate_token),  # ← token obrigatório
        db: Session = Depends(database_controller.get_db),
):
    try:
        result = db.execute(
            text("""
                INSERT INTO evento (evento_uid, nome, descricao, data, isactive, createdate, createuserid)
                VALUES (uuid_generate_v4(), :nome, :descricao, :data, 1, NOW(), 1)
                RETURNING evento_uid, nome, descricao, data, isactive
            """),
            {"nome": nome, "descricao": descricao, "data": data},
        )
        row = result.fetchone()
        db.commit()

        return {
            "id": str(row[0]),
            "nome": row[1],
            "descricao": row[2],
            "data": str(row[3]),
            "ativo": bool(row[4]),
        }

    except Exception as e:
        db.rollback()
        print(f"ERRO ao criar evento: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar evento: {str(e)}")


# ── EDITAR EVENTO ──────────────────────────────────────────────────────────────
@router.put("/update/admin/evento/{evento_uid}")
async def editar_evento(
        evento_uid: str,
        nome: str = Form(...),
        descricao: str = Form(...),
        data: str = Form(...),
        ativo: int = Form(1),
        user_data: dict = Depends(jwt_utils.validate_token),  # ← token obrigatório
        db: Session = Depends(database_controller.get_db),
):
    try:
        result = db.execute(
            text("""
                UPDATE evento
                SET nome       = :nome,
                    descricao  = :descricao,
                    data       = :data,
                    isactive   = :ativo,
                    changedate = NOW()
                WHERE evento_uid = :uid
                RETURNING evento_uid, nome, descricao, data, isactive
            """),
            {"nome": nome, "descricao": descricao, "data": data, "ativo": ativo, "uid": evento_uid},
        )
        row = result.fetchone()

        if not row:
            db.rollback()
            raise HTTPException(status_code=404, detail="Evento não encontrado")

        db.commit()

        return {
            "id": str(row[0]),
            "nome": row[1],
            "descricao": row[2],
            "data": str(row[3]),
            "ativo": bool(row[4]),
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"ERRO ao editar evento: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao editar evento: {str(e)}")


# ── DELETAR EVENTO ─────────────────────────────────────────────────────────────
@router.delete("/delete/admin/evento/{evento_uid}")
def deletar_evento(
        evento_uid: str,
        user_data: dict = Depends(jwt_utils.validate_token),  # ← token obrigatório
        db: Session = Depends(database_controller.get_db),
):
    try:
        db.execute(
            text("DELETE FROM evento_galeria WHERE evento_uid = :uid"),
            {"uid": evento_uid},
        )

        result = db.execute(
            text("DELETE FROM evento WHERE evento_uid = :uid RETURNING evento_uid"),
            {"uid": evento_uid},
        )
        deleted = result.fetchone()

        if not deleted:
            raise HTTPException(status_code=404, detail="Evento não encontrado")

        db.commit()
        return {"status": "success", "deleted_id": str(deleted[0])}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"ERRO ao deletar evento: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao deletar evento: {str(e)}")


# ── LISTAR ÁLBUM DO EVENTO ─────────────────────────────────────────────────────
@router.get("/get/evento/album/{evento_uid}")
def get_evento_album(
        evento_uid: str,
        user_data: dict = Depends(jwt_utils.validate_token),  # ← token obrigatório
        db: Session = Depends(database_controller.get_db)
):
    try:
        sql = text("""
            SELECT
                evento_galeria_uid,
                foto_nome,
                foto_mimetype,
                foto_tamanho,
                legenda,
                ordem,
                foto_dados
            FROM evento_galeria
            WHERE evento_uid = :evento_uid
              AND isactive   = 1
            ORDER BY ordem ASC
        """)

        result = db.execute(sql, {"evento_uid": evento_uid}).fetchall()

        album = []
        for r in result:
            foto_base64 = ""
            if r[6]:
                foto_base64 = f"data:{r[2]};base64,{base64.b64encode(r[6]).decode('utf-8')}"

            album.append({
                "id": str(r[0]),
                "foto_nome": r[1] or "sem_nome.png",
                "foto_mimetype": r[2] or "image/png",
                "foto_tamanho": r[3] or 0,
                "legenda": r[4] or "",
                "ordem": r[5] or 0,
                "foto_url": foto_base64,
            })

        return album

    except Exception as e:
        print(f"ERRO ao buscar álbum do evento: {e}")
        raise HTTPException(status_code=500, detail="Erro ao carregar álbum do evento")


# ── ADICIONAR FOTO AO ÁLBUM DO EVENTO ─────────────────────────────────────────
@router.post("/api/eventos/{evento_uid}/galeria")
async def adicionar_foto_evento(
        evento_uid: str,
        foto: UploadFile = File(...),
        legenda: str = Form(None),
        ordem: int = Form(0),
        user_data: dict = Depends(jwt_utils.validate_token),  # ← token obrigatório
        db: Session = Depends(database_controller.get_db),
):
    try:
        foto_bytes = await foto.read()

        result = db.execute(
            text("""
                INSERT INTO evento_galeria (
                    evento_galeria_uid, evento_uid,
                    foto_dados, foto_mimetype, foto_nome, foto_tamanho,
                    legenda, ordem, isactive, createdate, createuserid
                )
                VALUES (
                    uuid_generate_v4(), :evento_uid,
                    :foto_dados, :foto_mimetype, :foto_nome, :foto_tamanho,
                    :legenda, :ordem, 1, NOW(), 1
                )
                RETURNING evento_galeria_uid
            """),
            {
                "evento_uid": evento_uid,
                "foto_dados": foto_bytes,
                "foto_mimetype": foto.content_type,
                "foto_nome": foto.filename,
                "foto_tamanho": len(foto_bytes),
                "legenda": legenda,
                "ordem": ordem,
            },
        )
        db.commit()
        return {"id": str(result.fetchone()[0])}

    except Exception as e:
        db.rollback()
        print(f"ERRO ao inserir foto do evento: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── DELETAR FOTO DO ÁLBUM DO EVENTO ───────────────────────────────────────────
@router.delete("/api/admin/evento/album/delete/{evento_uid}/{foto_uid}")
def delete_evento_foto(
        evento_uid: str,
        foto_uid: str,
        user_data: dict = Depends(jwt_utils.validate_token),  # ← token obrigatório
        db: Session = Depends(database_controller.get_db),
):
    try:
        result = db.execute(
            text("""
                DELETE FROM evento_galeria
                WHERE evento_galeria_uid = :foto_uid
                  AND evento_uid         = :evento_uid
                RETURNING evento_galeria_uid
            """),
            {"foto_uid": foto_uid, "evento_uid": evento_uid},
        )
        db.commit()

        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Foto não encontrada")

        return {"deleted": foto_uid}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"ERRO ao deletar foto do evento: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao deletar foto: {str(e)}")