from fastapi import  Form
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
import database_controller
import jwt_utils

router = APIRouter()



# ── EDITAR EVENTO ──────────────────────────────────────────────────────────────
@router.put("/update/user/{usuario_id}")
async def editar_usuario(
        usuario_id: str,                    # ← era pessoauid
        nome: str = Form(...),
        telefone: str = Form(...),
        user_data: dict = Depends(jwt_utils.validate_token),
        db: Session = Depends(database_controller.get_db),
):
    try:
        result = db.execute(
            text("""
                UPDATE usuario
                SET nome      = :nome,
                    telefone  = :telefone
                WHERE id = :id
                RETURNING id, nome, telefone
            """),
            {"nome": nome, "telefone": telefone, "id": usuario_id},  # ← era "descricao"
        )

        row = result.fetchone()

        if not row:
            db.rollback()
            raise HTTPException(status_code=404, detail="Usuario não encontrado")

        db.commit()

        return {
            "id": usuario_id,
            "nome": row[0],
            "telefone": row[1],
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"ERRO ao editar usuario: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao editar usuario: {str(e)}")


