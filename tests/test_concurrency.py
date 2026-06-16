import concurrent.futures
import uuid
import pytest

def do_transfer(client, key, sender_id, receiver_id, amount):
    resp = client.post("/transactions", json={
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "amount": amount
    }, headers={"Idempotency-Key": key})
    return resp.status_code

@pytest.mark.asyncio
async def test_concurrent_transfers_conservation(client):
    # Create 10 accounts with 1000 each = 10000 total
    accounts = []
    for i in range(10):
        resp = client.post("/accounts", json={
            "owner_name": f"User{i}",
            "starting_balance": "1000.00"
        })
        accounts.append(resp.json()["id"])

    def get_balance(aid):
        return float(client.get(f"/accounts/{aid}").json()["balance"])

    start_total = sum(get_balance(aid) for aid in accounts)
    assert start_total == 10000.00

    # Fire 50 concurrent transfers using ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for i in range(50):
            sender = accounts[i % 10]
            receiver = accounts[(i + 1) % 10]
            key = str(uuid.uuid4())
            futures.append(
                executor.submit(do_transfer, client, key, sender, receiver, "10.00")
            )
        concurrent.futures.wait(futures)

    # Verify conservation of money
    end_total = sum(get_balance(aid) for aid in accounts)
    assert end_total == 10000.00
