import asyncio

from sqlalchemy import select

from app.core.database import async_session, init_db
from app.core.security import get_password_hash
from app.models.user import AppUser


async def seed_database() -> None:
    """Bootstrap only the admin account.

    No dummy orders, parties, or agents are created. All real data
    (orders, parties, agents) is populated by the on-premise sync agent.
    The admin user must exist because the sync agent authenticates as admin.
    """
    await init_db()

    async with async_session() as session:
        result = await session.execute(
            select(AppUser).where(AppUser.username == "admin")
        )
        if result.scalars().first():
            return

        session.add(
            AppUser(
                username="admin",
                password_hash=get_password_hash("admin123"),
                role="admin",
                party_code=None,
                agent_code=None,
                full_name="Balar Admin",
                email="admin@balar.in",
                is_active=True,
            )
        )
        await session.commit()
        print("Created admin user (no dummy data).")


if __name__ == "__main__":
    asyncio.run(seed_database())
