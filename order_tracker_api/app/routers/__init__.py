from app.routers.auth import router as auth_router
from app.routers.orders import router as orders_router
from app.routers.profile import router as profile_router
from app.routers.admin import router as admin_router

__all__ = ["auth_router", "orders_router", "profile_router", "admin_router"]
