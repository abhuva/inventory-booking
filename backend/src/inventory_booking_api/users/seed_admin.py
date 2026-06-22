import asyncio
import os

from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.core.database import AsyncSessionLocal
from inventory_booking_api.core.security import hash_password
from inventory_booking_api.users.enums import UserRole
from inventory_booking_api.users.models import User
from inventory_booking_api.users.session_service import get_user_by_email


async def seed_admin(session: AsyncSession, email: str, password: str, display_name: str) -> User:
    """Create or update the initial admin user."""

    normalized_email = email.lower()
    user = await get_user_by_email(session, normalized_email)
    if user is None:
        user = User(
            email=normalized_email,
            display_name=display_name,
            role=UserRole.ADMIN,
            password_hash=hash_password(password),
            is_active=True,
        )
        session.add(user)
    else:
        user.display_name = display_name
        user.role = UserRole.ADMIN
        user.password_hash = hash_password(password)
        user.is_active = True

    await session.commit()
    await session.refresh(user)
    return user


async def main() -> None:
    """Seed the initial admin from environment variables."""

    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")
    display_name = os.getenv("ADMIN_DISPLAY_NAME", "Admin")

    if not email or not password:
        raise SystemExit("ADMIN_EMAIL and ADMIN_PASSWORD are required.")

    async with AsyncSessionLocal() as session:
        user = await seed_admin(session, email=email, password=password, display_name=display_name)
        print(f"Seeded admin user: {user.email}")


if __name__ == "__main__":
    asyncio.run(main())
