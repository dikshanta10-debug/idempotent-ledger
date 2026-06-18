import uuid
import pytest
from contextlib import asynccontextmanager
from fastapi import FastAPI
import httpx
import fakeredis

@pytest.mark.asyncio
async def test_transfer_success(client):
    alice = (await client.post("/accounts", json={"owner_name": "Alice", "starting_balance": "1000.00"})).json()
    bob = (await client.post("/accounts", json={"owner_name": "Bob", "starting_balance": "500.00"})).json()
    
    key = str(uuid.uuid4())
    resp = await client.post("/transactions", json={
        "sender_id": alice["id"],
        "receiver_id": bob["id"],
        "amount": "200.00"
    }, headers={"Idempotency-Key": key})
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["amount"] == "200.00"
    
    alice_after = (await client.get(f"/accounts/{alice['id']}")).json()
    bob_after = (await client.get(f"/accounts/{bob['id']}")).json()
    assert alice_after["balance"] == "800.00"
    assert bob_after["balance"] == "700.00"

@pytest.mark.asyncio
async def test_idempotency_duplicate(client):
    alice = (await client.post("/accounts", json={"owner_name": "Alice", "starting_balance": "1000.00"})).json()
    bob = (await client.post("/accounts", json={"owner_name": "Bob", "starting_balance": "500.00"})).json()
    
    key = str(uuid.uuid4())
    payload = {"sender_id": alice["id"], "receiver_id": bob["id"], "amount": "100.00"}
    headers = {"Idempotency-Key": key}
    
    first = await client.post("/transactions", json=payload, headers=headers)
    second = await client.post("/transactions", json=payload, headers=headers)
    
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    
    alice_after = (await client.get(f"/accounts/{alice['id']}")).json()
    bob_after = (await client.get(f"/accounts/{bob['id']}")).json()
    assert alice_after["balance"] == "900.00"
    assert bob_after["balance"] == "600.00"

@pytest.mark.asyncio
async def test_insufficient_funds(client):
    alice = (await client.post("/accounts", json={"owner_name": "Alice", "starting_balance": "100.00"})).json()
    bob = (await client.post("/accounts", json={"owner_name": "Bob", "starting_balance": "500.00"})).json()
    
    resp = await client.post("/transactions", json={
        "sender_id": alice["id"],
        "receiver_id": bob["id"],
        "amount": "500.00"
    }, headers={"Idempotency-Key": str(uuid.uuid4())})
    
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Insufficient funds"

@pytest.mark.asyncio
async def test_missing_idempotency_key(client):
    alice = (await client.post("/accounts", json={"owner_name": "Alice", "starting_balance": "1000.00"})).json()
    bob = (await client.post("/accounts", json={"owner_name": "Bob", "starting_balance": "500.00"})).json()
    
    resp = await client.post("/transactions", json={
        "sender_id": alice["id"],
        "receiver_id": bob["id"],
        "amount": "10.00"
    })
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_negative_amount(client):
    alice = (await client.post("/accounts", json={"owner_name": "Alice", "starting_balance": "1000.00"})).json()
    bob = (await client.post("/accounts", json={"owner_name": "Bob", "starting_balance": "500.00"})).json()
    
    resp = await client.post("/transactions", json={
        "sender_id": alice["id"],
        "receiver_id": bob["id"],
        "amount": "-10.00"
    }, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_get_transaction_status(client):
    alice = (await client.post("/accounts", json={"owner_name": "Alice", "starting_balance": "1000.00"})).json()
    bob = (await client.post("/accounts", json={"owner_name": "Bob", "starting_balance": "500.00"})).json()
    
    key = str(uuid.uuid4())
    txn = (await client.post("/transactions", json={
        "sender_id": alice["id"],
        "receiver_id": bob["id"],
        "amount": "50.00"
    }, headers={"Idempotency-Key": key})).json()
    
    resp = await client.get(f"/transactions/{txn['id']}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "COMPLETED"

@pytest.mark.asyncio
async def test_ledger_entries_after_transfer(client):
    alice = (await client.post("/accounts", json={"owner_name": "Alice", "starting_balance": "1000.00"})).json()
    bob = (await client.post("/accounts", json={"owner_name": "Bob", "starting_balance": "500.00"})).json()
    
    await client.post("/transactions", json={
        "sender_id": alice["id"],
        "receiver_id": bob["id"],
        "amount": "200.00"
    }, headers={"Idempotency-Key": str(uuid.uuid4())})
    
    alice_ledger = (await client.get(f"/accounts/{alice['id']}/ledger")).json()
    bob_ledger = (await client.get(f"/accounts/{bob['id']}/ledger")).json()
    
    assert len(alice_ledger["items"]) == 1
    assert alice_ledger["items"][0]["entry_type"] == "DEBIT"
    assert alice_ledger["items"][0]["amount"] == "200.00"
    
    assert len(bob_ledger["items"]) == 1
    assert bob_ledger["items"][0]["entry_type"] == "CREDIT"
    assert bob_ledger["items"][0]["amount"] == "200.00"

@pytest.mark.asyncio
async def test_sender_not_found(client):
    resp = await client.post("/transactions", json={
        "sender_id": str(uuid.uuid4()),
        "receiver_id": str(uuid.uuid4()),
        "amount": "10.00"
    }, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert resp.status_code == 404
    assert "Sender" in resp.json()["detail"]

@pytest.mark.asyncio
async def test_receiver_not_found(client):
    alice = (await client.post("/accounts", json={"owner_name": "Alice", "starting_balance": "1000.00"})).json()
    resp = await client.post("/transactions", json={
        "sender_id": alice["id"],
        "receiver_id": str(uuid.uuid4()),
        "amount": "10.00"
    }, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert resp.status_code == 404
    assert "Receiver" in resp.json()["detail"]

@pytest.mark.asyncio
async def test_ledger_pagination(client):
    alice = (await client.post("/accounts", json={"owner_name": "Alice", "starting_balance": "1000.00"})).json()
    bob = (await client.post("/accounts", json={"owner_name": "Bob", "starting_balance": "500.00"})).json()
    
    await client.post("/transactions", json={
        "sender_id": alice["id"],
        "receiver_id": bob["id"],
        "amount": "100.00"
    }, headers={"Idempotency-Key": str(uuid.uuid4())})
    await client.post("/transactions", json={
        "sender_id": alice["id"],
        "receiver_id": bob["id"],
        "amount": "50.00"
    }, headers={"Idempotency-Key": str(uuid.uuid4())})
    
    resp = await client.get(f"/accounts/{alice['id']}/ledger?page=1&size=1")
    data = resp.json()
    assert data["page"] == 1
    assert data["size"] == 1
    assert data["total"] == 2
    assert len(data["items"]) == 1
    
    resp2 = await client.get(f"/accounts/{alice['id']}/ledger?page=2&size=1")
    data2 = resp2.json()
    assert data2["page"] == 2
    assert len(data2["items"]) == 1
    assert data2["items"][0]["id"] != data["items"][0]["id"]

@pytest.mark.asyncio
async def test_transaction_not_found(client):
    resp = await client.get(f"/transactions/{uuid.uuid4()}")
    assert resp.status_code == 404

# ---- New tests to boost coverage ----

@pytest.mark.asyncio
async def test_idempotency_conflict(client, fake_redis):
    """Test 409 Conflict when same key is in-flight."""
    key = str(uuid.uuid4())
    lock_key = f"lock:{key}"
    await fake_redis.set(lock_key, "1")

    alice = (await client.post("/accounts", json={"owner_name": "Alice", "starting_balance": "1000.00"})).json()
    bob = (await client.post("/accounts", json={"owner_name": "Bob", "starting_balance": "500.00"})).json()

    resp = await client.post("/transactions", json={
        "sender_id": alice["id"],
        "receiver_id": bob["id"],
        "amount": "10.00"
    }, headers={"Idempotency-Key": key})

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Transaction with this idempotency key is currently being processed"


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Cover app.main by calling /health on the real app with a dummy lifespan."""
    from app.main import app as real_app

    @asynccontextmanager
    async def dummy_lifespan(app: FastAPI):
        yield

    real_app.router.lifespan_context = dummy_lifespan

    # Override dependencies so the lifespan doesn't try to connect to real DB/Redis
    from app.database import get_db
    from app.redis_client import get_redis

    async def override_get_db():
        yield None

    async def override_get_redis():
        return fakeredis.FakeAsyncRedis(decode_responses=True)

    real_app.dependency_overrides[get_db] = override_get_db
    real_app.dependency_overrides[get_redis] = override_get_redis

    transport = httpx.ASGITransport(app=real_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
