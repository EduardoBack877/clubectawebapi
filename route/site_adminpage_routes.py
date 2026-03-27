
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text

from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

import database_controller

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
@router.put("/{ambientes_uid}")
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
            UPDATE ambientes
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
@router.delete("/{ambientes_uid}")
def deletar_ambiente(
    ambientes_uid: str,
    db: Session = Depends(database_controller.get_db),
):
    try:
        result = db.execute(text("""
            DELETE FROM ambientes
            WHERE ambientes_uid=:uid
            RETURNING ambientes_uid
        """), {"uid": ambientes_uid})

        db.commit()

        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Ambiente não encontrado")

        return {"deleted": ambientes_uid}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao deletar ambiente: {str(e)}")


# ── LISTAR AMBIENTES ────────────────────────────────────────────
@router.get("/api/ambientes")
def listar_ambientes(db: Session = Depends(database_controller.get_db)):
    try:
        # Adicionei todas as colunas no GROUP BY para evitar erro de sintaxe SQL
        # E troquei a.createdate por a.ambientes_uid caso a coluna createdate não exista
        query = text("""
            SELECT
                a.ambientes_uid, a.nome, a.descricao, a.capacidade, a.isactive,
                a.capa_mimetype, a.capa_nome,
                COUNT(g.ambiente_galeria_uid) AS total_fotos
            FROM ambiente a
            LEFT JOIN ambiente_galeria g ON g.ambientes_uid = a.ambientes_uid
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


# ── INSERIR FOTO NA GALERIA ─────────────────────────────────────
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


# ── DELETAR FOTO ────────────────────────────────────────────────
@router.delete("/{ambientes_uid}/galeria/{foto_uid}")
def deletar_foto(ambientes_uid: str, foto_uid: str, db: Session = Depends(database_controller.get_db)):
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


@router.get("/get/ambiente/album/{ambientes_uid}")
def get_ambiente_album(ambientes_uid: str, db: Session = Depends(database_controller.get_db)):
    try:
        result = db.execute(text("""Select ambiente_galeria_uid,
                                     foto_dados, 
                                     foto_mimetype, 
                                     foto_nome, 
                                     foto_tamanho, 
                                     legenda, 
                                     ordem from ambiente_galeria where ambiente_uid = :ambientes_uid"""),
                            {"ambientes_uid": ambientes_uid}).fetchall()

        return [
            {
                "id": str(r[0]),
                "foto_nome": r[1],
                "legenda": r[4],
                "ordem": r[5],
                "url": f"/ambientes/{ambientes_uid}/galeria/{r[0]}/imagem",
            }
            for r in result
        ]

        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao deletar foto: {str(e)}")