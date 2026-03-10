"""HookahBook — main FastAPI application."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import engine
from app.limiter import limiter
from app.logging_config import setup_logging
from app.middleware.logging_middleware import RequestLoggingMiddleware
from app.routers import auth, bookings, guest, health, master_recommendations, orders, tables, tobaccos, venue

# ---------------------------------------------------------------------------
# Logging — configure structlog before any logger is used
# ---------------------------------------------------------------------------
setup_logging(debug=settings.debug)


# --- App lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create data directory for SQLite (derived from DATABASE_URL)
    db_path = settings.database_url.split("///")[-1]
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    yield

    await engine.dispose()


# --- FastAPI app ---
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# --- Rate limiter ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


# --- Request logging (bind request_id + ip, emit http_request log) ---
app.add_middleware(RequestLoggingMiddleware)


# --- Security headers middleware ---
@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "0"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if settings.app_env == "production":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


# --- Routers ---
app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(venue.router, prefix="/api")
app.include_router(tables.router, prefix="/api")
app.include_router(tobaccos.router, prefix="/api")
app.include_router(bookings.router, prefix="/api")
app.include_router(guest.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(master_recommendations.router, prefix="/api")
