from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.database import (
    check_database_connection,
    create_tables,
)
from app.core.qdrant import (
    check_qdrant_connection,
)

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.rbac_test import (
    router as rbac_test_router,
)
from app.api.documents import (
    router as documents_router,
)
from app.api.chat import (
    router as chat_router,
)
from app.api.agent import (
    router as agent_router,
)
from app.api.evaluation import (
    router as evaluation_router,
)


# =========================================================
# Startup / Shutdown
# =========================================================

@asynccontextmanager
async def lifespan(
    app: FastAPI,
):

    print()
    print("=" * 60)
    print(
        f"{settings.APP_NAME} starting..."
    )
    print("=" * 60)

    # -----------------------------------------------------
    # Create Database Tables
    # -----------------------------------------------------

    try:

        create_tables()

        print(
            "Database tables ready."
        )

    except Exception as e:

        print(
            f"Database table creation failed: {e}"
        )

    # -----------------------------------------------------
    # Database Connection
    # -----------------------------------------------------

    database_status = (
        check_database_connection()
    )

    if database_status:

        print(
            "MySQL connection: OK"
        )

    else:

        print(
            "MySQL connection: FAILED"
        )

    # -----------------------------------------------------
    # Qdrant Connection
    # -----------------------------------------------------

    qdrant_status = (
        check_qdrant_connection()
    )

    if qdrant_status:

        print(
            "Qdrant connection: OK"
        )

    else:

        print(
            "Qdrant connection: FAILED"
        )

    print("=" * 60)
    print()

    yield

    print()
    print(
        f"{settings.APP_NAME} shutting down..."
    )


# =========================================================
# FastAPI Application
# =========================================================

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "EnterpriseIQ - "
        "Agentic RAG Enterprise Knowledge Assistant"
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# =========================================================
# Routers
# =========================================================

app.include_router(
    auth_router
)

app.include_router(
    users_router
)

app.include_router(
    rbac_test_router
)

app.include_router(
    documents_router
)

app.include_router(
    chat_router
)

app.include_router(
    agent_router
)

app.include_router(
    evaluation_router
)


# =========================================================
# Health Check
# =========================================================

@app.get(
    "/",
    tags=["Health"],
)
def root():

    return {
        "application": settings.APP_NAME,
        "status": "running",
        "version": "1.0.0",
    }


@app.get(
    "/health",
    tags=["Health"],
)
def health_check():

    database_status = (
        check_database_connection()
    )

    qdrant_status = (
        check_qdrant_connection()
    )

    overall_status = (
        database_status
        and qdrant_status
    )

    return {
        "status": (
            "healthy"
            if overall_status
            else "unhealthy"
        ),
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