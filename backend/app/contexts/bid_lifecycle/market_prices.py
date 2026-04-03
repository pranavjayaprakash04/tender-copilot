from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

if TYPE_CHECKING:
    pass


class MarketPrice(Base):
    """Materialized view model for market price analysis."""
    __tablename__ = "market_prices"

    tender_category: Mapped[str] = mapped_column(String(100), primary_key=True)
    portal: Mapped[str] = mapped_column(String(100), primary_key=True)
    avg_estimated_value: Mapped[float] = mapped_column(Float, nullable=False)
    min_value: Mapped[float] = mapped_column(Float, nullable=False)
    max_value: Mapped[float] = mapped_column(Float, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    last_refreshed: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return f"MarketPrice(category={self.tender_category}, portal={self.portal}, avg={self.avg_estimated_value})"
