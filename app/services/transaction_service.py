import json
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Account, Transaction, LedgerEntry, TransactionStatus
from app.schemas import TransactionRequest
from app.redis_client import get_redis
from app.config import settings
from fastapi import HTTPException

async def process_transaction(
    db: AsyncSession,
    idempotency_key: str,
    request: TransactionRequest
) -> dict:
    redis = await get_redis()
    idem_key = f"idempotency:{idempotency_key}"
    lock_key = f"lock:{idempotency_key}"

    # 1. Check cache
    cached = await redis.get(idem_key)
    if cached:
        return json.loads(cached)

    # 2. Check if in-flight
    lock_acquired = await redis.setnx(lock_key, "1")
    if not lock_acquired:
        raise HTTPException(status_code=409, detail="Transaction with this idempotency key is currently being processed")
    try:
        await redis.expire(lock_key, 10)

        # Lock sender row
        sender = (await db.execute(
            select(Account).where(Account.id == request.sender_id).with_for_update()
        )).scalar_one_or_none()
        if not sender:
            raise HTTPException(status_code=404, detail="Sender account not found")
        if sender.balance < request.amount:
            raise HTTPException(status_code=400, detail="Insufficient funds")

        # Lock receiver row
        receiver = (await db.execute(
            select(Account).where(Account.id == request.receiver_id).with_for_update()
        )).scalar_one_or_none()
        if not receiver:
            raise HTTPException(status_code=404, detail="Receiver account not found")

        # Update balances
        sender.balance -= request.amount
        receiver.balance += request.amount

        # Create transaction record
        txn = Transaction(
            id=uuid.uuid4(),
            sender_id=request.sender_id,
            receiver_id=request.receiver_id,
            amount=request.amount,
            status=TransactionStatus.COMPLETED,
            idempotency_key=idempotency_key
        )
        db.add(txn)

        await db.flush()
        await db.refresh(txn)

        # Create ledger entries
        debit_entry = LedgerEntry(
            transaction_id=txn.id,
            account_id=request.sender_id,
            entry_type="DEBIT",
            amount=request.amount
        )
        credit_entry = LedgerEntry(
            transaction_id=txn.id,
            account_id=request.receiver_id,
            entry_type="CREDIT",
            amount=request.amount
        )
        db.add_all([debit_entry, credit_entry])

        # Commit everything
        await db.commit()

        # Prepare result
        result = {
            "id": str(txn.id),
            "sender_id": str(txn.sender_id),
            "receiver_id": str(txn.receiver_id),
            "amount": str(txn.amount),
            "status": txn.status.value,
            "idempotency_key": txn.idempotency_key,
            "created_at": txn.created_at.isoformat(),
            "completed_at": txn.created_at.isoformat()
        }

        # Cache result
        await redis.setex(idem_key, settings.idempotency_ttl_seconds, json.dumps(result))
        return result

    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise
    finally:
        await redis.delete(lock_key)

async def get_transaction(db: AsyncSession, txn_id: uuid.UUID):
    result = await db.execute(select(Transaction).where(Transaction.id == txn_id))
    return result.scalar_one_or_none()
