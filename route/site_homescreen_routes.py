from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import text

import database_controller

router = APIRouter()


@router.get("/get/homescreen/ambientes")
def get_ambientes(db=Depends(database_controller.get_db)):

    import base64
    try:
        result = db.execute(text("""
            SELECT 
                a.ambientes_uid,
                a.nome,
                a.descricao,
                a.capacidade,
                a.capa_dados,
                a.capa_mimetype,
                r.data_reserva
            FROM ambiente a
            LEFT JOIN reservas r 
                ON r.ambientes_uid = a.ambientes_uid
                AND r.status = 'confirmada'
            WHERE a.isactive = 1
        """)).fetchall()

        ambientes_dict = {}

        for row in result:
            data = row._mapping

            uid = str(data["ambientes_uid"])

            if uid not in ambientes_dict:

                img = None
                if data["capa_dados"]:
                    base64_img = base64.b64encode(data["capa_dados"]).decode("utf-8")
                    img = f"data:{data['capa_mimetype']};base64,{base64_img}"

                ambientes_dict[uid] = {
                    "id": uid,
                    "nome": data["nome"],
                    "desc": data["descricao"],
                    "capacidade": data["capacidade"],
                    "img": img,  # 🔥 AGORA VEM DO BANCO
                    "indisponiveis": []
                }

            if data["data_reserva"]:
                ambientes_dict[uid]["indisponiveis"].append(data["data_reserva"].day)

        return list(ambientes_dict.values())

    except Exception as e:
        print("🔥 ERRO BACKEND:", e)
        return {"erro": str(e)}
