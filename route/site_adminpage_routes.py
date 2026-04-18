from fastapi import UploadFile, File, Form, APIRouter, Depends, HTTPException
from fastapi.responses import Response
from typing import Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
import base64
import database_controller

router = APIRouter()


# ── LISTAR EVENTOS ─────────────────────────────────────────────────────────────
@router.get("/api/eventos")
def listar_eventos(db: Session = Depends(database_controller.get_db)):
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
                "id":         str(r[0]),
                "nome":       r[1],
                "descricao":  r[2],
                "data":       str(r[3]),
                "ativo":      bool(r[4]),
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
    nome:      str = Form(...),
    descricao: str = Form(...),
    data:      str = Form(...),
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
            "id":        str(row[0]),
            "nome":      row[1],
            "descricao": row[2],
            "data":      str(row[3]),
            "ativo":     bool(row[4]),
        }

    except Exception as e:
        db.rollback()
        print(f"ERRO ao criar evento: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar evento: {str(e)}")


# ── EDITAR EVENTO ──────────────────────────────────────────────────────────────
@router.put("/update/admin/evento/{evento_uid}")
async def editar_evento(
    evento_uid: str,
    nome:       str = Form(...),
    descricao:  str = Form(...),
    data:       str = Form(...),
    ativo:      int = Form(1),
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
            "id":        str(row[0]),
            "nome":      row[1],
            "descricao": row[2],
            "data":      str(row[3]),
            "ativo":     bool(row[4]),
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
    db: Session = Depends(database_controller.get_db),
):
    try:
        # Galeria é deletada em cascata pelo ON DELETE CASCADE da FK,
        # mas caso queira garantir manualmente:
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
def get_evento_album(evento_uid: str, db: Session = Depends(database_controller.get_db)):
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
                "id":           str(r[0]),
                "foto_nome":    r[1] or "sem_nome.png",
                "foto_mimetype": r[2] or "image/png",
                "foto_tamanho": r[3] or 0,
                "legenda":      r[4] or "",
                "ordem":        r[5] or 0,
                "foto_url":     foto_base64,
            })

        return album

    except Exception as e:
        print(f"ERRO ao buscar álbum do evento: {e}")
        raise HTTPException(status_code=500, detail="Erro ao carregar álbum do evento")


# ── ADICIONAR FOTO AO ÁLBUM DO EVENTO ─────────────────────────────────────────
@router.post("/api/eventos/{evento_uid}/galeria")
async def adicionar_foto_evento(
    evento_uid: str,
    foto:    UploadFile = File(...),
    legenda: str        = Form(None),
    ordem:   int        = Form(0),
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
                "evento_uid":    evento_uid,
                "foto_dados":    foto_bytes,
                "foto_mimetype": foto.content_type,
                "foto_nome":     foto.filename,
                "foto_tamanho":  len(foto_bytes),
                "legenda":       legenda,
                "ordem":         ordem,
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
    foto_uid:   str,
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