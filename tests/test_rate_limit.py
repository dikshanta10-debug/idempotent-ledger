import uuid

def test_rate_limit(client):
    alice = client.post("/accounts", json={"owner_name": "Alice", "starting_balance": "1000.00"}).json()
    bob = client.post("/accounts", json={"owner_name": "Bob", "starting_balance": "500.00"}).json()
    
    # Send 10 requests (within limit)
    for i in range(10):
        resp = client.post("/transactions", json={
            "sender_id": alice["id"],
            "receiver_id": bob["id"],
            "amount": "1.00"
        }, headers={"Idempotency-Key": str(uuid.uuid4())})
        assert resp.status_code == 200
    
    # 11th request should be rate limited
    resp = client.post("/transactions", json={
        "sender_id": alice["id"],
        "receiver_id": bob["id"],
        "amount": "1.00"
    }, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert resp.status_code == 429
