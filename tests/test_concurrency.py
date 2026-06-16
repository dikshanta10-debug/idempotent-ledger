import uuid
import pytest

@pytest.mark.asyncio
async def test_concurrent_transfers_conservation(client):
    accounts = []
    for i in range(10):
        resp = await client.post("/accounts", json={
            "owner_name": f"User{i}",
            "starting_balance": "1000.00"
        })
        accounts.append(resp.json()["id"])

    async def get_balance(aid):
        resp = await client.get(f"/accounts/{aid}")
        return float(resp.json()["balance"])

    start_total = sum([await get_balance(aid) for aid in accounts])
    assert start_total == 10000.00

    for i in range(50):
        sender = accounts[i % 10]
        receiver = accounts[(i + 1) % 10]
        resp = await client.post("/transactions", json={
            "sender_id": sender,
            "receiver_id": receiver,
            "amount": "10.00"
        }, headers={"Idempotency-Key": str(uuid.uuid4())})
        assert resp.status_code == 200

    end_total = sum([await get_balance(aid) for aid in accounts])
    assert end_total == 10000.00
