from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("jobs.id"), nullable=False, index=True
    )
    sensor_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    antecedente: Mapped[str] = mapped_column(Text, nullable=False)
    consecuente: Mapped[str] = mapped_column(String(50), nullable=False)
    n_vars: Mapped[int] = mapped_column(Integer, nullable=False)
    soporte: Mapped[float] = mapped_column(Float, nullable=False)
    confianza: Mapped[float] = mapped_column(Float, nullable=False)
    lift: Mapped[float] = mapped_column(Float, nullable=False)

    job: Mapped["Job"] = relationship("Job", back_populates="rules")  # noqa: F821
