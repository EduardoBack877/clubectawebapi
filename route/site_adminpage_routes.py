from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional

import database_controller

router = APIRouter(prefix="/ambientes", tags=["Ambientes"])


# ── CRIAR AMBIENTE ─────────────────────────────────────────────
@router.post("/")
async def criar_ambiente(
    nome: str = Form(...),
    descricao: str = Form(...),
    capacidade: int = Form(0),
    ativo: int = Form(1),
    img: Optional[UploadFile] = File(None),
    db: Session = Depends(database_controller.get_db),
):
    try:
        capa_dados, capa_mimetype, capa_nome = None, None, None

        if img:
            capa_dados = await img.read()
            capa_mimetype = img.content_type
            capa_nome = img.filename

        result = db.execute(text("""
            INSERT INTO ambientes (
                ambientes_uid, nome, descricao, capacidade, isactive,
                capa_dados, capa_mimetype, capa_nome, createuserid
            )
            VALUES (uuid_generate_v4(), :nome, :descricao, :capacidade, :ativo,
                    :capa_dados, :capa_mimetype, :capa_nome, 1)
            RETURNING ambientes_uid, nome, descricao, capacidade, isactive
        """), {
            "nome": nome,
            "descricao": descricao,
            "capacidade": capacidade,
            "ativo": ativo,
            "capa_dados": capa_dados,
            "capa_mimetype": capa_mimetype,
            "capa_nome": capa_nome,
        })

        db.commit()
        row = result.fetchone()

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
@router.get("/")
def listar_ambientes(db: Session = Depends(database_controller.get_db)):
    try:
        rows = db.execute(text("""
            SELECT
                a.ambientes_uid, a.nome, a.descricao, a.capacidade, a.isactive,
                a.capa_mimetype, a.capa_nome,
                COUNT(g.ambiente_galeria_uid) AS total_fotos
            FROM ambientes a
            LEFT JOIN ambiente_galeria g ON g.ambientes_uid = a.ambientes_uid
            WHERE a.isactive = true
            GROUP BY a.ambientes_uid
            ORDER BY a.createdate DESC
        """)).fetchall()

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
        raise HTTPException(status_code=500, detail=f"Erro ao listar ambientes: {str(e)}")


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
@router.post("/{ambientes_uid}/galeria")
async def adicionar_foto(
    ambientes_uid: str,
    foto: UploadFile = File(...),
    legenda: str = Form(default=None),
    ordem: int = Form(default=0),
    db: Session = Depends(database_controller.get_db),
):
    try:
        foto_bytes = await foto.read()

        if len(foto_bytes) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Imagem excede 10 MB")

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
        new_uid = result.fetchone()[0]

        return {"id": str(new_uid)}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao adicionar foto: {str(e)}")


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