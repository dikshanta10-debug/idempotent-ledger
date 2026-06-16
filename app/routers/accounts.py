from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import AccountCreate, AccountResponse, PaginatedLedger, LedgerEntryResponse
from app.services import account_service
from uuid import UUID

router = APIRouter(prefix="/accounts", tags=["accounts"])

@router.post("", response_model=AccountResponse, status_code=201)
async def create_account(data: AccountCreate, db: AsyncSession = Depends(get_db)):
    account = await account_service.create_account(db, data)
    return account

@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(account_id: UUID, db: AsyncSession = Depends(get_db)):
    account = await account_service.get_account(db, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account

@router.get("/{account_id}/ledger", response_model=PaginatedLedger)
async def get_ledger(
    account_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    # verify account exists
    account = await account_service.get_account(db, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    entries, total = await account_service.get_ledger_entries(db, account_id, page, size)
    return PaginatedLedger(
        items=[LedgerEntryResponse.model_validate(e) for e in entries],
        page=page,
        size=size,
        total=total
    )
