from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

import database_controller
import jwt_utils
router = APIRouter()


@router.get("/get/usuario/historico-reservas")
def get_historico_reservas(
        # O 'payload' conterá os dados que você decodificou no validate_token
        user_data: dict = Depends(jwt_utils.validate_token),
        db: Session = Depends(database_controller.get_db)
):
    try:
        # Extraímos o ID do usuário diretamente do payload validado
        usuario_id = user_data.get("id")

        query = text("""
            SELECT 
                r.reservas_uid, 
                a.nome AS nome_ambiente, 
                r.data_reserva, 
                r.hora_inicio, 
                r.hora_fim, 
                r.status 
            FROM reservas r
            JOIN ambiente a ON a.ambientes_uid = r.ambientes_uid
            WHERE r.isactive = 1 AND r.usuarioid = :uid
            ORDER BY r.data_reserva DESC, r.hora_inicio DESC
        """)

        result = db.execute(query, {"uid": usuario_id})
        reservas = result.fetchall()

        return [
            {
                "reservas_uid": str(r.reservas_uid),
                "ambiente_nome": r.nome_ambiente,
                "data_reserva": str(r.data_reserva),
                "hora_inicio": r.hora_inicio.strftime('%H:%M') if hasattr(r.hora_inicio, 'strftime') else str(
                    r.hora_inicio)[:5],
                "hora_fim": r.hora_fim.strftime('%H:%M') if hasattr(r.hora_fim, 'strftime') else str(r.hora_fim)[:5],
                "status": r.status,
            }
            for r in reservas
        ]

    except Exception as e:
        print(f"Erro ao buscar histórico: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar histórico")