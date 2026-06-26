from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AppUser(Base):
    __tablename__ = "app_users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # admin, agent, party
    party_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # for party users
    agent_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # for agent users
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    last_login: Mapped[Optional[datetime]] = mapped_column(nullable=True)
