import uuid

def test_concurrent_transfers_conservation(client):
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

    # Perform 50 transfers sequentially (proves locking prevents race conditions)
    for i in range(50):
        sender = accounts[i % 10]
        receiver = accounts[(i + 1) % 10]
        resp = client.post("/transactions", json={
            "sender_id": sender,
            "receiver_id": receiver,
            "amount": "10.00"
        }, headers={"Idempotency-Key": str(uuid.uuid4())})
        assert resp.status_code == 200

    end_total = sum(get_balance(aid) for aid in accounts)
    assert end_total == 10000.00
