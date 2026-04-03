import os

import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DB_USER = "avnadmin"
DB_PASS = "AVNS_wMcqRiWHbGZih48G-f_"
DB_HOST = "pg-23b57d82-clinicasaovicente.b.aivencloud.com"
DB_PORT = "22679"
DB_NAME = "defaultdb"
SSLM_ODE = "require"

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode={SSLM_ODE}"

# ✅ Pool de conexões persistentes em vez de NullPool
# pool_size      → conexões abertas e mantidas prontas
# max_overflow   → conexões extras permitidas em pico
# pool_timeout   → tempo máximo esperando uma conexão livre (segundos)
# pool_recycle   → recicla conexões mais velhas que X segundos (evita timeout do servidor)
# pool_pre_ping  → testa a conexão antes de usar (evita conexões mortas)
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=15,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()