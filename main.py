import sys
import os
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from sqlalchemy import text
from fastapi.staticfiles import StaticFiles

import controller_user_authenticate
from BCryptHasher import BcryptHasher

from database_controller import get_db



# Routes
from route import (
    site_login_routes,
    site_homescreen_routes,
    site_adminpage_routes,
    site_paginadetalhada_routes
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

# ✅ apenas UM middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(site_login_routes.router)
app.include_router(site_homescreen_routes.router)
app.include_router(site_adminpage_routes.router)
app.include_router(site_paginadetalhada_routes.router)
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