import sys
import os
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from sqlalchemy import text

import controller_user_authenticate
from BCryptHasher import BcryptHasher

from database_controller import get_db

# # Models (força o PyInstaller a incluir)
# from model.consulta_model import Consulta
# from model.produto_model import Grupo, Subgrupo, Produto
# from model.movimentacao_model import Movimentacao, MovimentacaoItem
# from model.motivo_saida_model import MotivoSaida  # ← ADICIONE AQUI

# Routes
from route import (
 site_login_routes
)


# =========================
# CONFIGURAÇÃO DE LOG
# =========================
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LOG_PATH = os.path.join(BASE_DIR, "error_log.txt")
sys.stderr = open(LOG_PATH, "a", encoding="utf-8")

# =========================
# LIFESPAN
# =========================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🔍 Testando conexão com o banco de dados...")
    try:
        db = next(get_db())
        db.execute(text("SELECT 1;"))
        print("✅ Conexão com o banco de dados bem-sucedida!")
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco de dados: {e}")
    finally:
        try:
            db.close()
        except Exception:
            pass

    yield

    print("🛑 Encerrando aplicação...")

# =========================
# FASTAPI APP
# =========================
app = FastAPI(
    title="API São Vicente",
    lifespan=lifespan
)



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # depois você restringe
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# ROTAS
# =========================
# app.include_router(controller_user_authenticate.router)
# app.include_router(pessoa_routes.router)
# app.include_router(cidade_routes.router)
# app.include_router(empresa_routes.router)
# app.include_router(tipoconvenio_routes.router)
# app.include_router(usuario_routes.router)
# app.include_router(parterecepcao_routes.router)
# app.include_router(cid_routes.router)
# app.include_router(partemedico_routes.router)
# app.include_router(cat_routes.router)
# app.include_router(PDFWeb_routes.router)
# app.include_router(consulta_routes.router)
# app.include_router(cartao_routes.router)
# app.include_router(cadastrar_convidado_routes.router)
# app.include_router(produto_routes.router)                   # ← NOVO
# app.include_router(fornecedor_routes.router)
# app.include_router(entrada_estoque_routes.router)
# app.include_router(saida_estoque_routes.router)
# app.include_router(inadimplencia_routes.router)
app.include_router(site_login_routes.router)
# =========================
# START DO UVICORN (EXE SAFE)
# =========================
def start():
    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8001,
        log_config=None,
        access_log=False
    )

if __name__ == "__main__":
    start()