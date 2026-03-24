# DAO/UserDAO.py

from sqlalchemy.orm import Session
from BCryptHasher import BcryptHasher
# 🔑 Importa as funções de geração de token
from jwt_utils import generate_token_for_user

# Importação do modelo (Mantenha o modelo real no seu arquivo de modelos)
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = 'usuario'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    senha = Column(String)
    isactive = Column(Boolean)  # smallint mapeado para Boolean
    passwordversion = Column(Integer)
    document = Column(String)
    nome = Column(String)
    ismedico = Column(Boolean)  # smallint mapeado para Boolean
    createuserid = Column(Integer)
    isfeminino = Column(Boolean)
    createdate = Column(DateTime)
    changeuserid = Column(Integer)
    changedate = Column(DateTime)
    CRM = Column(String)
    RQE = Column(String)
    tipoassinatura = Column(String)
    especialidade = Column(String)
    UF = Column(String)


class UserDAO:
    def __init__(self, db_session: Session):
        self.db = db_session

    def data_to_generate_token(self, email: str, senha: str) -> str | None:
        """
        Autentica o usuário e, se bem-sucedido, retorna a string do Token JWT.
        """
        # 1. Busca o usuário e o hash
        user = self.db.query(User).filter(
            User.email == email,
            User.isactive == 1  # Usando True booleano
        ).first()

        if not user:
            return None

        # 2. Verifica a senha
        hasher = BcryptHasher()
        stored_hash = user.senha

        if not hasher.verify_password(senha, stored_hash):
            return None

        # 3. 🔑 Prepara os dados para o JWT
        user_details = {
            "id": user.id,
            "email": user.email,
            "document": user.document,
            "passwordversion": user.passwordversion,  # Usando o case correto
            "nome": user.nome,
            "ismedico": user.ismedico,
            "crm": user.CRM,
            "rqe": user.RQE,
            "tipoassinatura": user.tipoassinatura,
            "especialidade": user.especialidade,
            "uf": user.UF,
            "isfeminino": user.isfeminino,
        }

        # 4. Gera e retorna APENAS a string do token
        access_token = generate_token_for_user(user_details)

        return access_token