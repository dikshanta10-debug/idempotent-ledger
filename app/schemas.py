from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal

# --- Account ---
class AccountCreate(BaseModel):
    owner_name: str = Field(..., min_length=1, max_length=255)
    starting_balance: Decimal = Field(default=Decimal("0.00"), ge=0)

class AccountResponse(BaseModel):
    id: UUID
    owner_name: str
    balance: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Transaction ---
class TransactionRequest(BaseModel):
    sender_id: UUID
    receiver_id: UUID
    amount: Decimal = Field(..., gt=0)

class TransactionResponse(BaseModel):
    id: UUID
    sender_id: UUID
    receiver_id: UUID
    amount: Decimal
    status: str
    idempotency_key: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# --- Ledger ---
class LedgerEntryResponse(BaseModel):
    id: UUID
    transaction_id: UUID
    entry_type: str
    amount: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PaginatedLedger(BaseModel):
    items: List[LedgerEntryResponse]
    page: int
    size: int
    total: int
