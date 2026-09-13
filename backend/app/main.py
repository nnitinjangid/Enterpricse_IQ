from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import (
    check_database_connection,
    create_tables,
)
from app.core.qdrant import check_qdrant_connection

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.rbac_test import router as rbac_test_router
from app.api.documents import router as documents_router
from app.api.chat import router as chat_router
from app.api.agent import router as agent_router
from app.api.evaluation import router as evaluation_router


app = FastAPI(
    title=settings.APP_NAME,
    description="EnterpriseIQ - Agentic RAG Platform",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5501",
        "http://localhost:5501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def startup_event():
    print("=" * 60)
    print("EnterpriseIQ starting...")
    print("=" * 60)

    print(
        f"Application : {settings.APP_NAME}"
    )

    print(
        f"Environment : {settings.APP_ENV}"
    )

    database_status = check_database_connection()

    if database_status:
        print("MySQL       : Connected")
    else:
        print("MySQL       : Connection failed")

    qdrant_status = check_qdrant_connection()

    if qdrant_status:
        print("Qdrant      : Connected")
    else:
        print("Qdrant      : Connection failed")

    create_tables()

    print("Database tables checked.")
    print("=" * 60)


# ============================================================
# HEALTH
# ============================================================

@app.get("/")
def root():
    return {
        "message": "EnterpriseIQ API is running.",
        "version": "1.0.0",
    }


@app.get("/health")
def health():
    database_status = check_database_connection()
    qdrant_status = check_qdrant_connection()

    return {
        "status": "healthy",
        "database": (
            "connected"
            if database_status
            else "disconnected"
        ),
        "qdrant": (
            "connected"
            if qdrant_status
            else "disconnected"
        ),
    }


# ============================================================
# API ROUTERS
# ============================================================

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(rbac_test_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(agent_router)
app.include_router(evaluation_router)