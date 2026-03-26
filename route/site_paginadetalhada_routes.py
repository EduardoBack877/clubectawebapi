from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import text
import base64
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


@router.get("/api/ambientes/{ambientes_uid}/reservas")
def get_reservas(ambientes_uid: str, db=Depends(database_controller.get_db)):
    try:
        # 2. Adicionado o reservas_uid no SELECT para poder retornar no JSON
        sql = text("""
            SELECT 
                reservas_uid,
                data_reserva,
                hora_inicio,
                hora_fim,
                status
            FROM RESERVAS
            WHERE ambientes_uid = :id
        """)

        result = db.execute(sql, {"id": ambientes_uid}).fetchall()

        if not result:
            # Retornar lista vazia em vez de 404 costuma ser melhor para o Flutter não quebrar
            return []

        # 3. Mapeamento correto pelos índices (0 a 4)
        return [
            {
                "reservas_uid": str(r[0]),
                "data_reserva": str(r[1]),  # Converter date para string
                "hora_inicio": str(r[2]),  # Converter time para string
                "hora_fim": str(r[3]),  # Converter time para string
                "status": r[4],
            }
            for r in result
        ]
    except Exception as e:
        # 4. Corrigido erro de concatenação: str(e)
        print(f"Erro ao buscar reservas: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@router.get("/api/galeria/{ambientes_uid}")
def get_galeria(ambientes_uid: str, db=Depends(database_controller.get_db)):
    try:
        sql = text("""
            SELECT 
                ambiente_galeria_uid,
                foto_dados,
                foto_mimetype,
                legenda,
                ordem
            FROM ambiente_galeria
            WHERE ambientes_uid = :ambientes_uid
            ORDER BY ordem ASC
        """)

        # A execução correta no SQLAlchemy:
        query_result = db.execute(sql, {"ambientes_uid": ambientes_uid}).fetchall()
        if not query_result:
            return []

        return [
            {
                "ambiente_galeria_uid": str(r[0]),
                # O r[1] é o campo bytea (binário) do banco
                "foto_dados": base64.b64encode(r[1]).decode('utf-8') if r[1] else None,
                "foto_mimetype": r[2],
                "legenda": r[3],
                "ordem": r[4],
            }
            for r in query_result
        ]



    except Exception as e:
        print(f"Erro ao buscar galeria: {e}")
        raise HTTPException(status_code=500, detail=str(e))
