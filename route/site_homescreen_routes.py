from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import text

import database_controller

router = APIRouter()


@router.get("/get/homescreen/ambientes")
def get_ambientes(db=Depends(database_controller.get_db)):

    result = db.execute(text("""
        SELECT 
            a.ambientes_uid,
            a.nome,
            a.descricao,
            a.capacidade,
            r.data_reserva
        FROM ambiente a
        LEFT JOIN reservas r 
            ON r.ambientes_uid = a.ambientes_uid
            AND r.status = 'confirmada'
        WHERE a.isactive = 1
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
                "img": "https://picsum.photos/400/300",
                "indisponiveis": []
            }

        if data["data_reserva"]:
            ambientes_dict[uid]["indisponiveis"].append(data["data_reserva"].day)

    return list(ambientes_dict.values())

