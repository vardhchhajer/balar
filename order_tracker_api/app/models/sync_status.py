from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SyncStatus(Base):
    __tablename__ = "sync_status"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    last_sync_time: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="never")  # never, syncing, success, failed
    records_synced: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    triggered_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # auto, admin_force
