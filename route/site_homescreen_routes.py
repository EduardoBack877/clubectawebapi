from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import text

import database_controller

router = APIRouter()


@router.get("/get/homescreen/ambientes")
def get_ambientes(db=Depends(database_controller.get_db)):

    result = db.execute(text("""
        SELECT 
            ambientes_uid,
            nome,
            descricao,
            capacidade
        FROM ambiente
        WHERE isactive = 1
    """)).fetchall()

    ambientes_dict = {}

    for row in result:
        data = row._mapping  # 👈 chave mágica

        uid = str(data["ambientes_uid"])

        if uid not in ambientes_dict:
            ambientes_dict[uid] = {
                "id": uid,
                "nome": data["nome"],
                "desc": data["descricao"],
                "capacidade": data["capacidade"],
                "img": "https://picsum.photos/400/300"
            }


    return list(ambientes_dict.values())

