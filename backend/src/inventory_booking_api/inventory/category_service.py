from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.audit.enums import AuditAction
from inventory_booking_api.audit.service import write_audit_log
from inventory_booking_api.inventory.category_schemas import CategoryCreate, CategoryUpdate
from inventory_booking_api.inventory.models import Category
from inventory_booking_api.users.models import User


async def list_categories(session: AsyncSession) -> list[Category]:
    result = await session.execute(select(Category).order_by(Category.name))
    return list(result.scalars().all())


async def get_category(session: AsyncSession, category_id: UUID) -> Category | None:
    return await session.get(Category, category_id)


async def create_category(session: AsyncSession, payload: CategoryCreate, actor: User) -> Category:
    category = Category(**payload.model_dump())
    session.add(category)
    await session.flush()
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.CREATE,
        entity_type="category",
        entity_id=category.id,
        summary=f"Created category {category.name}",
    )
    await session.commit()
    await session.refresh(category)
    return category


async def update_category(
    session: AsyncSession,
    category: Category,
    payload: CategoryUpdate,
    actor: User,
) -> Category:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type="category",
        entity_id=category.id,
        summary=f"Updated category {category.name}",
    )
    await session.commit()
    await session.refresh(category)
    return category
