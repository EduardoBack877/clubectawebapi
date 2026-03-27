import bcrypt

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

import database_controller
import jwt_utils
from jwt_utils import create_access_token

router = APIRouter()


class RegisterPayload(BaseModel):
    email: str
    password: str
    name: str
    sex: str
    phone: str

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

        if(data.sex == "M"):
            sex = 1
        else:
            sex = 0


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
                isactive,
                telefone
            )
            VALUES (:email, :senha, :nome, :sex, 1, 1, :telefone)
        """), {
            "email": data.email,
            "senha": senha_hash,
            "nome": data.name,
            "sex":  sex,
            "telefone": data.phone
        })

        db.commit()

        return {"message": "Usuário criado com sucesso"}

    except Exception as e:
        print("ERRO:", e)
        raise HTTPException(status_code=500, detail=str(e))


class LoginPayload(BaseModel):
    email: str
    password: str


@router.post("/auth/login")
def login(data: LoginPayload, db=Depends(database_controller.get_db)):
    try:

        result = db.execute(
            text("SELECT id,nome,senha FROM usuario WHERE email = :email"),
            {"email": data.email}
        )
        user = result.fetchone()

        if not user:
            raise HTTPException(status_code=400, detail="Usuário não encontrado")

        senha_hash = user[2]

        if not bcrypt.checkpw(
            data.password.encode("utf-8"),
            senha_hash.encode("utf-8")
        ):
            raise HTTPException(status_code=400, detail="Senha inválida")

        token = create_access_token({
            "user_id": user[0],
            "email": data.email,
        })

        print(user[1])

        return {
            "token": token,
            "name": user[1],
            "type": "bearer"
        }


    except Exception as e:
        print("ERRO LOGIN:", e)
        raise HTTPException(status_code=500, detail=str(e))