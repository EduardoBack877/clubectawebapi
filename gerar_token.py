from datetime import datetime, timedelta
from jose import jwt

SECRET_KEY = "78d3b31e3f9c1ceb8ed59655eed31c7a95eb015f9b8cb51982a64ed807d4b83f2ba886a45dac39750f1dedd231e30a74c11ed19f5e76b400dbab372d"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hora

def gerar_token(usuario_id: int, password_version: int) -> str:
    """Gera JWT com usuario_id e password_version"""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "usuario_id": usuario_id,
        "password_version": password_version,
        "exp": expire
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token
