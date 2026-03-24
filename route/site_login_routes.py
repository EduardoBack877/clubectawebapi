import bcrypt

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

import database_controller

router = APIRouter()


class RegisterPayload(BaseModel):
    email: str
    password: str
    name: str
    sex: str

from sqlalchemy import text, INTEGER


@router.post("/auth/register")
def register(data: RegisterPayload, db=Depends(database_controller.get_db)):
    try:
        # verifica se já existe
        result = db.execute(
            text("SELECT id FROM usuario WHERE email = :email"),
            {"email": data.email}
        )

        if result.fetchone():
            raise HTTPException(status_code=400, detail="E-mail já cadastrado")

        senha_hash = bcrypt.hashpw(
            data.password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        db.execute(text("""
            INSERT INTO usuario (
                email,
                senha,
                nome,
                isfeminino,
                isvisitante,
                isactive
            )
            VALUES (:email, :senha, :nome, :sex, 0, 1)
        """), {
            "email": data.email,
            "senha": senha_hash,
            "nome": data.name,
            "sex":  int(data.sex)
        })

        db.commit()

        return {"message": "Usuário criado com sucesso"}

    except Exception as e:
        print("ERRO:", e)
        raise HTTPException(status_code=500, detail=str(e))