from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import UUID as SQLAlchemyUUID
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class WhatsAppSession(Base):
    """WhatsApp session model."""
    __tablename__ = "whatsapp_sessions"

    id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, primary_key=True, default=func.uuid_generate_v4())
    company_id: Mapped[UUID] = mapped_column(SQLAlchemyUUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    phone_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    is_opted_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    session_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_flow: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"WhatsAppSession(id={self.id}, phone={self.phone_number})"
