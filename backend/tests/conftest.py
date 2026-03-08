"""Shared test fixtures — in-memory SQLite, async client, seed factories."""

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app
from app.models.enums import BookingStatus, TableShape, UserRole
from app.models.venue import Venue
from app.models.table import Table
from app.models.tobacco import Tobacco
from app.models.user import User
from app.models.booking import Booking
from app.models.guest import Guest
from app.services.security import (
    create_access_token,
    create_refresh_token,
    encrypt_phone,
    hash_password,
    hash_phone,
)


# ---------------------------------------------------------------------------
# Engine & session for tests (in-memory SQLite)
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite://"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    """Override default event loop to session scope."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset in-memory rate limit counters before each test."""
    from app.limiter import limiter
    if hasattr(limiter, "_storage") and hasattr(limiter._storage, "reset"):
        limiter._storage.reset()
    yield


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Per-test fresh database: create all tables, yield session, drop."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSession() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTPX async client with DB dependency overridden."""

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def venue(db_session: AsyncSession) -> Venue:
    """Create a test venue."""
    v = Venue(name="Test Lounge", address="ул. Тестовая, 1", phone="+71234567890")
    db_session.add(v)
    await db_session.flush()
    await db_session.refresh(v)
    return v


@pytest_asyncio.fixture
async def owner(db_session: AsyncSession, venue: Venue) -> User:
    """Create an owner user."""
    u = User(
        venue_id=venue.id,
        login="owner",
        password_hash=hash_password("owner123"),
        role=UserRole.owner,
        display_name="Owner",
    )
    db_session.add(u)
    await db_session.flush()
    await db_session.refresh(u)
    return u


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession, venue: Venue) -> User:
    """Create an admin user."""
    u = User(
        venue_id=venue.id,
        login="admin",
        password_hash=hash_password("admin123"),
        role=UserRole.admin,
        display_name="Admin",
    )
    db_session.add(u)
    await db_session.flush()
    await db_session.refresh(u)
    return u


@pytest_asyncio.fixture
async def hookah_master(db_session: AsyncSession, venue: Venue) -> User:
    """Create a hookah_master user (limited role)."""
    u = User(
        venue_id=venue.id,
        login="master",
        password_hash=hash_password("master123"),
        role=UserRole.hookah_master,
        display_name="Master",
    )
    db_session.add(u)
    await db_session.flush()
    await db_session.refresh(u)
    return u


def _make_auth_cookies(user: User) -> dict[str, str]:
    """Generate access_token cookie value for a user."""
    token_data = {
        "sub": str(user.id),
        "venue_id": user.venue_id,
        "role": user.role.value,
    }
    access = create_access_token(token_data)
    refresh = create_refresh_token(token_data)
    return {"access_token": access, "refresh_token": refresh}


@pytest_asyncio.fixture
async def owner_client(
    client: AsyncClient, owner: User
) -> AsyncClient:
    """Client authenticated as owner."""
    cookies = _make_auth_cookies(owner)
    client.cookies.set("access_token", cookies["access_token"])
    client.cookies.set("refresh_token", cookies["refresh_token"])
    return client


@pytest_asyncio.fixture
async def admin_client(
    client: AsyncClient, admin_user: User
) -> AsyncClient:
    """Client authenticated as admin."""
    cookies = _make_auth_cookies(admin_user)
    client.cookies.set("access_token", cookies["access_token"])
    client.cookies.set("refresh_token", cookies["refresh_token"])
    return client


@pytest_asyncio.fixture
async def master_client(
    client: AsyncClient, hookah_master: User
) -> AsyncClient:
    """Client authenticated as hookah_master."""
    cookies = _make_auth_cookies(hookah_master)
    client.cookies.set("access_token", cookies["access_token"])
    client.cookies.set("refresh_token", cookies["refresh_token"])
    return client


@pytest_asyncio.fixture
async def table(db_session: AsyncSession, venue: Venue) -> Table:
    """Create a test table."""
    t = Table(
        venue_id=venue.id,
        number=1,
        capacity=4,
        x=100,
        y=100,
        width=80,
        height=80,
        shape=TableShape.rect,
    )
    db_session.add(t)
    await db_session.flush()
    await db_session.refresh(t)
    return t


@pytest_asyncio.fixture
async def table2(db_session: AsyncSession, venue: Venue) -> Table:
    """Create a second test table."""
    t = Table(
        venue_id=venue.id,
        number=2,
        capacity=6,
        x=300,
        y=100,
        width=100,
        height=100,
        shape=TableShape.circle,
    )
    db_session.add(t)
    await db_session.flush()
    await db_session.refresh(t)
    return t


@pytest_asyncio.fixture
async def tobacco(db_session: AsyncSession, venue: Venue) -> Tobacco:
    """Create a test tobacco."""
    t = Tobacco(
        venue_id=venue.id,
        name="Darkside Supernova",
        brand="Darkside",
        strength=4,
        flavor_profile=["citrus", "mint"],
        in_stock=True,
    )
    db_session.add(t)
    await db_session.flush()
    await db_session.refresh(t)
    return t


@pytest_asyncio.fixture
async def tobacco_out_of_stock(db_session: AsyncSession, venue: Venue) -> Tobacco:
    """Create an out-of-stock tobacco."""
    t = Tobacco(
        venue_id=venue.id,
        name="Tangiers Cane Mint",
        brand="Tangiers",
        strength=5,
        flavor_profile=["mint"],
        in_stock=False,
    )
    db_session.add(t)
    await db_session.flush()
    await db_session.refresh(t)
    return t


@pytest_asyncio.fixture
async def booking(db_session: AsyncSession, venue: Venue, table: Table) -> Booking:
    """Create a test booking (pending status)."""
    from datetime import date, time

    phone = "+79991234567"
    # Create guest
    guest = Guest(
        phone_hash=hash_phone(phone),
        phone_encrypted=encrypt_phone(phone),
        name="Тестовый Гость",
    )
    db_session.add(guest)
    await db_session.flush()
    await db_session.refresh(guest)

    b = Booking(
        venue_id=venue.id,
        table_id=table.id,
        guest_id=guest.id,
        guest_phone_encrypted=encrypt_phone(phone),
        guest_name="Тестовый Гость",
        date=date(2026, 6, 15),
        time_from=time(19, 0),
        time_to=time(22, 0),
        guest_count=3,
        status=BookingStatus.pending,
        notes="Тестовое бронирование",
    )
    db_session.add(b)
    await db_session.flush()
    await db_session.refresh(b)
    return b
