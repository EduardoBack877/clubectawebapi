# jwt_utils.py
import json
import jwt
import datetime
from typing import Any

from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from sqlalchemy import text
from sqlalchemy.orm import Session

import database_controller

SECRET_KEY = "78d3b31e3f9c1ceb8ed59655eed31c7a95eb015f9b8cb51982a64ed807d4b83f2ba886a45dac39750f1dedd231e30a74c11ed19f5e76b400dbab372d"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# 🔐 Objeto correto para leitura do header Authorization: Bearer TOKEN
security = HTTPBearer()


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def generate_token_for_user(user_details: dict) -> str | None:
    if not user_details:
        return None

    token_payload = {
        "id": user_details.get("id"),
        "email": user_details.get("email"),
        "document": user_details.get("document"),
        "passwordVersion": user_details.get("passwordversion"),
        "nome": user_details.get("nome"),
        "isfeminino": user_details.get("isfeminino"),
        "crm": user_details.get("crm"),
        "rqe": user_details.get("rqe"),
        "isAdmin": user_details.get("isadmin"),
    }

    try:
        return create_access_token(token_payload)
    except Exception as e:
        print(f"Erro ao gerar o token JWT: {e}")
        return None


# REMOVA O "async". Deixe como "def" normal para evitar bloqueio com drivers síncronos.
def validate_token(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(database_controller.get_db)  # <-- Usamos a conexão reaproveitável do Pool
):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print("PAYLOAD DECODIFICADO:", payload)

        user_id = payload.get("id")
        email = payload.get("email")
        document = payload.get("document")
        password_version = payload.get("passwordVersion")

        if not all([user_id, email]):
            raise HTTPException(status_code=400, detail="Dados insuficientes")

        # Query rápida usando a Sessão do SQLAlchemy (muito mais rápido que raw connection)
        # Usamos SELECT 1 para ser o mais leve possível
        result = db.execute(
            text("""
                SELECT 1 FROM usuario 
                WHERE id = :uid 
                AND isactive = 1
                LIMIT 1
            """),
            {"uid": user_id}
        ).fetchone()

        if not result:
            raise HTTPException(status_code=401, detail="Usuário inativo ou senha alterada")

        return payload

    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail="Token inválido")

def format_json(data: dict) -> str:
    return json.dumps(data, indent=4, sort_keys=True)
