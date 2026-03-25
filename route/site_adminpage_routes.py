from fastapi import APIRouter, UploadFile, File, Form
from typing import Optional
import uuid

import database_controller

router = APIRouter()

@router.post("/insert/admin/novo-ambiente")
async def criar_ambiente(
    nome: str = Form(...),
    descricao: str = Form(...),
    capacidade: int = Form(0),
    ativo: int = Form(1),
    img: Optional[UploadFile] = File(None),
):
    capa_dados = None
    capa_mimetype = None
    capa_nome = None

    # 📸 lê imagem
    if img:
        capa_dados = await img.read()  # 🔥 vira bytes (bytea)
        capa_mimetype = img.content_type
        capa_nome = img.filename

    # 🧠 INSERT no banco
    query = """
        INSERT INTO ambientes (
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
            %s, %s, %s, %s, %s, %s, %s, %s
        )
        RETURNING ambientes_uid, nome, descricao, capacidade, isactive;
    """

    values = (
        nome,
        descricao,
        capacidade,
        ativo,
        capa_dados,
        capa_mimetype,
        capa_nome,
        1  # user fixo (ou pega do auth depois)
    )

    conn = database_controller.get_db()  # sua conexão
    cur = conn.cursor()

    cur.execute(query, values)
    result = cur.fetchone()

    conn.commit()
    cur.close()
    conn.close()

    return {
        "id": str(result[0]),
        "nome": result[1],
        "descricao": result[2],
        "capacidade": result[3],
        "ativo": bool(result[4]),
    }