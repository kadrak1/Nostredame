"""Create the initial admin user for a venue.

Run: python scripts/create_admin.py
"""

import asyncio
import getpass
import sys

sys.path.insert(0, "backend")

from app.config import settings  # noqa: E402
from app.database import async_session, engine, Base  # noqa: E402
from app.models import Venue, User  # noqa: E402
from app.services.security import hash_password  # noqa: E402


async def main():
    print("=== Create Admin User ===")
    print()

    venue_name = input("Venue name: ").strip()
    if not venue_name:
        print("Venue name is required")
        return

    login = input("Admin login: ").strip()
    if not login:
        print("Login is required")
        return

    password = getpass.getpass("Admin password (min 8 chars): ").strip()
    if len(password) < 8:
        print("Password must be at least 8 characters")
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        venue = Venue(name=venue_name)
        session.add(venue)
        await session.flush()

        admin = User(
            venue_id=venue.id,
            login=login,
            password_hash=hash_password(password),
            role="owner",
            display_name="Admin",
        )
        session.add(admin)
        await session.commit()

        print()
        print(f"Venue '{venue_name}' created (ID: {venue.id})")
        print(f"Admin '{login}' created (role: owner)")
        print("You can now log in at /admin/login")


if __name__ == "__main__":
    asyncio.run(main())
