from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models import Account, LedgerEntry
from app.schemas import AccountCreate
from uuid import UUID
from typing import Optional

async def create_account(db: AsyncSession, data: AccountCreate) -> Account:
    account = Account(
        owner_name=data.owner_name,
        balance=data.starting_balance
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account

async def get_account(db: AsyncSession, account_id: UUID) -> Optional[Account]:
    result = await db.execute(select(Account).where(Account.id == account_id))
    return result.scalar_one_or_none()

async def get_ledger_entries(
    db: AsyncSession, 
    account_id: UUID, 
    page: int = 1, 
    size: int = 20
) -> tuple[list[LedgerEntry], int]:
    # Count total entries
    count_query = select(func.count()).select_from(LedgerEntry).where(LedgerEntry.account_id == account_id)
    total = (await db.execute(count_query)).scalar() or 0

    # Fetch paginated
    query = (
        select(LedgerEntry)
        .where(LedgerEntry.account_id == account_id)
        .order_by(LedgerEntry.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await db.execute(query)
    entries = result.scalars().all()
    return entries, total
