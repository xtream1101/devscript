from app.routes.auth_routes import router as auth_router
from app.routes.snippet_routes import router as snippet_router
from app.routes.web_routes import router as web_router
from app.routes.api_key_routes import router as api_key_router

__all__ = ["auth_router", "snippet_router", "web_router", "api_key_router"]
