from fastapi import APIRouter, UploadFile, File, Form, Depends
from typing import Optional
import uuid

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
        print("🔥 ERRO BACKEND:", e)
        return {"erro": str(e)}
