import asyncio
from datetime import date

from sqlalchemy import select

from app.core.database import async_session, init_db
from app.core.security import get_password_hash
from app.models.user import AppUser
from app.models.order import Order, OrderItem


async def seed_database() -> None:
    await init_db()

    async with async_session() as session:
        result = await session.execute(select(AppUser))
        if result.scalars().first():
            print("Database already seeded. Skipping.")
            return

        # Seed users: 1 admin, 1 agent, 2 parties
        users = [
            AppUser(
                username="admin",
                password_hash=get_password_hash("admin123"),
                role="admin",
                party_code=None,
                agent_code=None,
                full_name="Vardh Admin",
                email="admin@balar.in",
                is_active=True,
            ),
            AppUser(
                username="agent1",
                password_hash=get_password_hash("agent123"),
                role="agent",
                party_code=None,
                agent_code="AGT001",
                full_name="Ramesh Agent",
                email="ramesh@balar.in",
                is_active=True,
            ),
            AppUser(
                username="party1",
                password_hash=get_password_hash("party123"),
                role="party",
                party_code="PARTY001",
                agent_code=None,
                full_name="Rajesh Kumar",
                email="rajesh@acmecorp.com",
                is_active=True,
            ),
            AppUser(
                username="party2",
                password_hash=get_password_hash("party123"),
                role="party",
                party_code="PARTY002",
                agent_code=None,
                full_name="Suresh Patel",
                email="suresh@betaltd.com",
                is_active=True,
            ),
        ]

        session.add_all(users)
        await session.flush()

        orders = [
            Order(party_code="PARTY001", order_no="ORD-2024-001", order_date=date(2024, 10, 1), dispatch_status="Dispatched", dispatch_date=date(2024, 10, 5), invoice_no="INV-1001", tracking_no="TRK10001X", total_amount=15500.00, remarks="Fragile items"),
            Order(party_code="PARTY001", order_no="ORD-2024-002", order_date=date(2024, 10, 3), dispatch_status="Dispatched", dispatch_date=date(2024, 10, 7), invoice_no="INV-1002", tracking_no="TRK10002X", total_amount=8200.00, remarks=None),
            Order(party_code="PARTY001", order_no="ORD-2024-003", order_date=date(2024, 10, 8), dispatch_status="Delivered", dispatch_date=date(2024, 10, 12), invoice_no="INV-1003", tracking_no="TRK10003X", total_amount=23400.00, remarks="Delivered to warehouse"),
            Order(party_code="PARTY001", order_no="ORD-2024-004", order_date=date(2024, 10, 10), dispatch_status="Pending", dispatch_date=None, invoice_no=None, tracking_no=None, total_amount=5600.00, remarks="Awaiting stock"),
            Order(party_code="PARTY001", order_no="ORD-2024-005", order_date=date(2024, 10, 15), dispatch_status="Processing", dispatch_date=None, invoice_no=None, tracking_no=None, total_amount=12750.00, remarks=None),
            Order(party_code="PARTY002", order_no="ORD-2024-006", order_date=date(2024, 10, 18), dispatch_status="Dispatched", dispatch_date=date(2024, 10, 22), invoice_no="INV-2001", tracking_no="TRK20001X", total_amount=9800.00, remarks="Handle with care"),
            Order(party_code="PARTY002", order_no="ORD-2024-007", order_date=date(2024, 10, 20), dispatch_status="Pending", dispatch_date=None, invoice_no=None, tracking_no=None, total_amount=6800.00, remarks=None),
            Order(party_code="PARTY002", order_no="ORD-2024-008", order_date=date(2024, 10, 25), dispatch_status="Delivered", dispatch_date=date(2024, 11, 1), invoice_no="INV-2004", tracking_no="TRK20004X", total_amount=22100.00, remarks="Left at reception"),
        ]

        session.add_all(orders)
        await session.flush()

        order_items = [
            OrderItem(order_id=orders[0].id, product_name="Steel Rods 12mm", quantity=50, unit_price=200.0, amount=10000.0),
            OrderItem(order_id=orders[0].id, product_name="Cement Bags (50kg)", quantity=20, unit_price=250.0, amount=5000.0),
            OrderItem(order_id=orders[1].id, product_name="PVC Pipes 4inch", quantity=30, unit_price=180.0, amount=5400.0),
            OrderItem(order_id=orders[1].id, product_name="Pipe Fittings", quantity=40, unit_price=70.0, amount=2800.0),
            OrderItem(order_id=orders[2].id, product_name="Ceramic Tiles 2x2", quantity=200, unit_price=85.0, amount=17000.0),
            OrderItem(order_id=orders[2].id, product_name="Tile Adhesive 20kg", quantity=40, unit_price=120.0, amount=4800.0),
            OrderItem(order_id=orders[3].id, product_name="Electrical Wire 2.5mm", quantity=8, unit_price=450.0, amount=3600.0),
            OrderItem(order_id=orders[3].id, product_name="Switch Board Set", quantity=10, unit_price=200.0, amount=2000.0),
            OrderItem(order_id=orders[4].id, product_name="Paint Emulsion 20L", quantity=15, unit_price=650.0, amount=9750.0),
            OrderItem(order_id=orders[4].id, product_name="Paint Brushes Set", quantity=20, unit_price=150.0, amount=3000.0),
            OrderItem(order_id=orders[5].id, product_name="Glass Panels 6mm", quantity=14, unit_price=700.0, amount=9800.0),
            OrderItem(order_id=orders[6].id, product_name="Wood Planks Teak", quantity=8, unit_price=850.0, amount=6800.0),
            OrderItem(order_id=orders[7].id, product_name="Bathroom Fittings Set", quantity=10, unit_price=1500.0, amount=15000.0),
            OrderItem(order_id=orders[7].id, product_name="Water Heater 25L", quantity=5, unit_price=1420.0, amount=7100.0),
        ]

        session.add_all(order_items)
        await session.commit()
        print(f"Seeded {len(users)} users and {len(orders)} orders with {len(order_items)} items.")


if __name__ == "__main__":
    asyncio.run(seed_database())
