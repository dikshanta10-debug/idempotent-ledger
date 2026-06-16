import uuid
import pytest

@pytest.mark.asyncio
async def test_rate_limit(client):
    alice = (await client.post("/accounts", json={"owner_name": "Alice", "starting_balance": "1000.00"})).json()
    bob = (await client.post("/accounts", json={"owner_name": "Bob", "starting_balance": "500.00"})).json()
    
    for i in range(10):
        resp = await client.post("/transactions", json={
            "sender_id": alice["id"],
            "receiver_id": bob["id"],
            "amount": "1.00"
        }, headers={"Idempotency-Key": str(uuid.uuid4())})
        assert resp.status_code == 200
    
    resp = await client.post("/transactions", json={
        "sender_id": alice["id"],
        "receiver_id": bob["id"],
        "amount": "1.00"
    }, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert resp.status_code == 429
