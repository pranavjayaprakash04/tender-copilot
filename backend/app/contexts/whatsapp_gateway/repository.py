from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from app.database import Base
from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.database import get_async_session


class WhatsAppMessageLogModel(Base):
    """WhatsApp message log database model."""
    __tablename__ = "whatsapp_message_logs"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False, index=True)
    message_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)  # inbound, outbound
    from_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    to_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_metadata: Mapped[dict[str, Any] | None] = mapped_column(Text, nullable=True)  # JSON string
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class WhatsAppOptStatusModel(Base):
    """WhatsApp opt-in status database model."""
    __tablename__ = "whatsapp_opt_status"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False, unique=True, index=True)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    is_opted_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    opt_in_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opt_out_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_message_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class WhatsAppGatewayRepository:
    """Repository for WhatsApp gateway operations."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session or get_async_session().__anext__()

    async def create_message_log(
        self,
        company_id: UUID,
        message_id: str,
        direction: str,
        from_phone: str,
        to_phone: str,
        content: str,
        message_type: str,
        status: str = "pending",
        metadata: dict[str, Any] | None = None,
    ) -> WhatsAppMessageLogModel:
        """Create a new message log entry."""
        async with get_async_session() as session:
            log_entry = WhatsAppMessageLogModel(
                company_id=company_id,
                message_id=message_id,
                direction=direction,
                from_phone=from_phone,
                to_phone=to_phone,
                content=content,
                message_type=message_type,
                status=status,
                metadata=metadata,
            )
            session.add(log_entry)
            await session.commit()
            await session.refresh(log_entry)
            return log_entry

    async def update_message_status(
        self,
        message_id: str,
        status: str,
        sent_at: datetime | None = None,
        delivered_at: datetime | None = None,
        read_at: datetime | None = None,
        error_message: str | None = None,
    ) -> WhatsAppMessageLogModel | None:
        """Update message status and timestamps."""
        async with get_async_session() as session:
            stmt = (
                update(WhatsAppMessageLogModel)
                .where(WhatsAppMessageLogModel.message_id == message_id)
                .values(
                    status=status,
                    sent_at=sent_at,
                    delivered_at=delivered_at,
                    read_at=read_at,
                    error_message=error_message,
                )
                .returning(WhatsAppMessageLogModel)
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.scalar_one_or_none()

    async def get_message_logs(
        self,
        company_id: UUID | None = None,
        direction: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WhatsAppMessageLogModel]:
        """Get message logs with optional filtering."""
        async with get_async_session() as session:
            query = select(WhatsAppMessageLogModel)

            if company_id:
                query = query.where(WhatsAppMessageLogModel.company_id == company_id)
            if direction:
                query = query.where(WhatsAppMessageLogModel.direction == direction)

            query = query.order_by(WhatsAppMessageLogModel.created_at.desc()).limit(limit).offset(offset)

            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_or_create_opt_status(
        self,
        company_id: UUID,
        phone_number: str,
    ) -> WhatsAppOptStatusModel:
        """Get or create opt-in status for a company."""
        async with get_async_session() as session:
            # Try to get existing status
            stmt = select(WhatsAppOptStatusModel).where(WhatsAppOptStatusModel.company_id == company_id)
            result = await session.execute(stmt)
            opt_status = result.scalar_one_or_none()

            if opt_status:
                return opt_status

            # Create new opt status
            opt_status = WhatsAppOptStatusModel(
                company_id=company_id,
                phone_number=phone_number,
                is_opted_in=True,
                opt_in_date=datetime.utcnow(),
            )
            session.add(opt_status)
            await session.commit()
            await session.refresh(opt_status)
            return opt_status

    async def update_opt_status(
        self,
        company_id: UUID,
        is_opted_in: bool,
    ) -> WhatsAppOptStatusModel | None:
        """Update opt-in status for a company."""
        async with get_async_session() as session:
            stmt = (
                update(WhatsAppOptStatusModel)
                .where(WhatsAppOptStatusModel.company_id == company_id)
                .values(
                    is_opted_in=is_opted_in,
                    opt_out_date=datetime.utcnow() if not is_opted_in else None,
                    opt_in_date=datetime.utcnow() if is_opted_in else None,
                    updated_at=datetime.utcnow(),
                )
                .returning(WhatsAppOptStatusModel)
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.scalar_one_or_none()

    async def increment_message_count(
        self,
        company_id: UUID,
        last_message_date: datetime | None = None,
    ) -> WhatsAppOptStatusModel | None:
        """Increment message count for a company."""
        async with get_async_session() as session:
            stmt = (
                update(WhatsAppOptStatusModel)
                .where(WhatsAppOptStatusModel.company_id == company_id)
                .values(
                    message_count=WhatsAppOptStatusModel.message_count + 1,
                    last_message_date=last_message_date or datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                .returning(WhatsAppOptStatusModel)
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.scalar_one_or_none()

    async def get_opt_status(self, company_id: UUID) -> WhatsAppOptStatusModel | None:
        """Get opt-in status for a company."""
        async with get_async_session() as session:
            stmt = select(WhatsAppOptStatusModel).where(WhatsAppOptStatusModel.company_id == company_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_all_opt_statuses(
        self,
        opted_in_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WhatsAppOptStatusModel]:
        """Get all opt-in statuses with optional filtering."""
        async with get_async_session() as session:
            query = select(WhatsAppOptStatusModel)

            if opted_in_only:
                query = query.where(WhatsAppOptStatusModel.is_opted_in == True)

            query = query.order_by(WhatsAppOptStatusModel.updated_at.desc()).limit(limit).offset(offset)

            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_whatsapp_stats(self) -> dict[str, Any]:
        """Get WhatsApp gateway statistics."""
        async with get_async_session() as session:
            # Get opt-in stats
            opt_stmt = select(WhatsAppOptStatusModel)
            opt_result = await session.execute(opt_stmt)
            opt_statuses = list(opt_result.scalars().all())

            total_companies = len(opt_statuses)
            opted_in_companies = len([s for s in opt_statuses if s.is_opted_in])
            opted_out_companies = total_companies - opted_in_companies

            # Get message stats
            msg_stmt = select(WhatsAppMessageLogModel)
            msg_result = await session.execute(msg_stmt)
            messages = list(msg_result.scalars().all())

            total_messages_sent = len([m for m in messages if m.direction == "outbound"])
            total_messages_delivered = len([m for m in messages if m.status == "delivered"])
            total_messages_failed = len([m for m in messages if m.status == "failed"])

            delivery_rate = (total_messages_delivered / total_messages_sent * 100) if total_messages_sent > 0 else 0

            # Messages by type
            messages_by_type = {}
            for message in messages:
                msg_type = message.message_type
                messages_by_type[msg_type] = messages_by_type.get(msg_type, 0) + 1

            return {
                "total_companies": total_companies,
                "opted_in_companies": opted_in_companies,
                "opted_out_companies": opted_out_companies,
                "total_messages_sent": total_messages_sent,
                "total_messages_delivered": total_messages_delivered,
                "total_messages_failed": total_messages_failed,
                "delivery_rate": round(delivery_rate, 2),
                "messages_by_type": messages_by_type,
            }
