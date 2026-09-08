from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    answer: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    retrieval_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    relevance_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    faithfulness_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    citation_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )