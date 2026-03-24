from datetime import datetime, timedelta, timezone

import jwt as jwt
from fastapi import APIRouter, HTTPException, Header, status, Depends
from pydantic import BaseModel
from database_controller import get_db
from sqlalchemy.orm import Session


from DAO.UserDAO import UserDAO

router = APIRouter()


# Obtém a SECRET_KEY da variável de ambiente
SECRET_KEY = "1e255487c1c756ce12133c0762a16fe5779ca1d313470369436f32c2190f56d08eeb0aced2217aeba658a246ac773d01392478e341e56ee1c68a343270d38dfd"
#os.getenv("SECRET_KEY")

# Verifica se a SECRET_KEY está definida
if SECRET_KEY is None:
    raise ValueError("A variável de ambiente SECRET_KEY não está definida.")


def generate_jwt_token(id: int, email: str, document: str, passwordversion: str) -> str:
    # Define os dados do payload do token JWT
    current_time = datetime.now(timezone.utc)
    payload = {
        "id": id,
        "email": email,
        "document": document,
        "passwordversion": passwordversion

        #"exp": current_time + timedelta(seconds=3600)
    }

    # Gera o token JWT assinado com a chave secreta
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token

class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/user/authenticate", status_code=status.HTTP_200_OK)
async def authenticate_user(
    request_data: dict, # Ou seu Pydantic Model de Login
    db: Session = Depends(get_db)
):
    email = request_data.get("email")
    password = request_data.get("password")

    # Inicializa o DAO, passando a Session injetada
    user_dao = UserDAO(db)

    # user_token agora é a string do token JWT ou None
    user_token = user_dao.data_to_generate_token(email, password)

    if not user_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Retorna APENAS o token e a secret_key, conforme o cliente Flutter espera.
    # Usaremos a mesma chave para 'secret_key' que está no jwt_utils
    # Lembre-se, na produção, 'secret_key' NUNCA deve ser enviada ao cliente.
    SECRET_KEY_FOR_CLIENT = "78d3b31e3f9c1ceb8ed59655eed31c7a95eb015f9b8cb51982a64ed807d4b83f2ba886a45dac39750f1dedd231e30a74c11ed19f5e76b400dbab372d"

    return {
        "token": user_token,             # Token JWT gerado
        "secret_key": SECRET_KEY_FOR_CLIENT, # Chave fixa
    }