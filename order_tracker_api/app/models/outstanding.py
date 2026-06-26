from datetime import date, datetime
from typing import Optional

from sqlalchemy import String, Float, Date, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OutstandingBill(Base):
    __tablename__ = "outstanding_bills"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    party_code: Mapped[str] = mapped_column(String(50), nullable=False)
    bill_no: Mapped[str] = mapped_column(String(50), nullable=False)
    bill_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    amount_paid: Mapped[float] = mapped_column(Float, default=0.0)
    amount_outstanding: Mapped[float] = mapped_column(Float, nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
