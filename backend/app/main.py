from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.rbac_test import router as rbac_test_router
from app.api.users import router as users_router
from app.api.search import router as search_router
from app.api.chat import router as chat_router
from app.api.agent import router as agent_router

from app.core.config import settings

from app.core.database import (
    check_database_connection,
    create_tables,
)

from app.core.qdrant import (
    check_qdrant_connection,
)


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "EnterpriseIQ - "
        "Agentic Enterprise Knowledge Assistant"
    ),
    version="1.0.0",
)


# =========================================================
# Startup
# =========================================================

@app.on_event("startup")
def startup_event():
    create_tables()


# =========================================================
# API Routers
# =========================================================

app.include_router(
    auth_router
)

app.include_router(
    rbac_test_router
)

app.include_router(
    users_router
)

app.include_router(
    documents_router
)

app.include_router(
    search_router
)

app.include_router(
    chat_router
)

app.include_router(
    agent_router
)


# =========================================================
# Health APIs
# =========================================================

@app.get("/health")
def health_check():

    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }


@app.get("/health/db")
def database_health_check():

    database_connected = (
        check_database_connection()
    )

    return {
        "database": "mysql",
        "connected": database_connected,
    }


@app.get("/health/qdrant")
def qdrant_health_check():

    qdrant_connected = (
        check_qdrant_connection()
    )

    return {
        "qdrant": "connected"
        if qdrant_connected
        else "disconnected",
        "connected": qdrant_connected,
    }