from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings


engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


Base = declarative_base()


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def check_database_connection():
    try:

        with engine.connect() as connection:

            connection.execute(
                text("SELECT 1")
            )

        return True

    except Exception as e:

        print(
            f"Database connection error: {e}"
        )

        return False


def create_tables():

    from app.models import (
        User,
        Document,
        DocumentChunk,
        Conversation,
        Message,
        Evaluation,
    )

    Base.metadata.create_all(
        bind=engine
    )