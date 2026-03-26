from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import text

import database_controller

router = APIRouter()

@router.get("/ambientes/{ambiente_id}/capa")
def get_capa(ambiente_id: str, db=Depends(database_controller.get_db)):
    try:
        result = db.execute(text("""
            SELECT capa_dados, capa_mimetype
            FROM ambiente
            WHERE ambientes_uid = :id
        """), {"id": ambiente_id}).fetchone()

        if not result or not result[0]:
            raise HTTPException(status_code=404, detail="Imagem não encontrada")

        capa_dados, capa_mimetype = result

        return Response(
            content=capa_dados,
            media_type=capa_mimetype
        )

    except Exception as e:
        print("🔥 ERRO BACKEND:", e)
        return {"erro": str(e)}