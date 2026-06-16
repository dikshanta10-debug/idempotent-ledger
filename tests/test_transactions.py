import uuid
import pytest

def test_transfer_success(client):
    alice = client.post("/accounts", json={"owner_name": "Alice", "starting_balance": "1000.00"}).json()
    bob = client.post("/accounts", json={"owner_name": "Bob", "starting_balance": "500.00"}).json()
    
    key = str(uuid.uuid4())
    resp = client.post("/transactions", json={
        "sender_id": alice["id"],
        "receiver_id": bob["id"],
        "amount": "200.00"
    }, headers={"Idempotency-Key": key})
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["amount"] == "200.00"
    
    alice_after = client.get(f"/accounts/{alice['id']}").json()
    bob_after = client.get(f"/accounts/{bob['id']}").json()
    assert alice_after["balance"] == "800.00"
    assert bob_after["balance"] == "700.00"

def test_idempotency_duplicate(client):
    alice = client.post("/accounts", json={"owner_name": "Alice", "starting_balance": "1000.00"}).json()
    bob = client.post("/accounts", json={"owner_name": "Bob", "starting_balance": "500.00"}).json()
    
    key = str(uuid.uuid4())
    payload = {
        "sender_id": alice["id"],
        "receiver_id": bob["id"],
        "amount": "100.00"
    }
    headers = {"Idempotency-Key": key}
    
    first = client.post("/transactions", json=payload, headers=headers)
    second = client.post("/transactions", json=payload, headers=headers)
    
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    
    alice_after = client.get(f"/accounts/{alice['id']}").json()
    bob_after = client.get(f"/accounts/{bob['id']}").json()
    assert alice_after["balance"] == "900.00"
    assert bob_after["balance"] == "600.00"

def test_insufficient_funds(client):
    alice = client.post("/accounts", json={"owner_name": "Alice", "starting_balance": "100.00"}).json()
    bob = client.post("/accounts", json={"owner_name": "Bob", "starting_balance": "500.00"}).json()
    
    resp = client.post("/transactions", json={
        "sender_id": alice["id"],
        "receiver_id": bob["id"],
        "amount": "500.00"
    }, headers={"Idempotency-Key": str(uuid.uuid4())})
    
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Insufficient funds"

def test_missing_idempotency_key(client):
    alice = client.post("/accounts", json={"owner_name": "Alice", "starting_balance": "1000.00"}).json()
    bob = client.post("/accounts", json={"owner_name": "Bob", "starting_balance": "500.00"}).json()
    
    resp = client.post("/transactions", json={
        "sender_id": alice["id"],
        "receiver_id": bob["id"],
        "amount": "10.00"
    })
    assert resp.status_code == 422

def test_negative_amount(client):
    alice = client.post("/accounts", json={"owner_name": "Alice", "starting_balance": "1000.00"}).json()
    bob = client.post("/accounts", json={"owner_name": "Bob", "starting_balance": "500.00"}).json()
    
    resp = client.post("/transactions", json={
        "sender_id": alice["id"],
        "receiver_id": bob["id"],
        "amount": "-10.00"
    }, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert resp.status_code == 422

def test_get_transaction_status(client):
    alice = client.post("/accounts", json={"owner_name": "Alice", "starting_balance": "1000.00"}).json()
    bob = client.post("/accounts", json={"owner_name": "Bob", "starting_balance": "500.00"}).json()
    
    key = str(uuid.uuid4())
    txn = client.post("/transactions", json={
        "sender_id": alice["id"],
        "receiver_id": bob["id"],
        "amount": "50.00"
    }, headers={"Idempotency-Key": key}).json()
    
    resp = client.get(f"/transactions/{txn['id']}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "COMPLETED"

def test_ledger_entries_after_transfer(client):
    alice = client.post("/accounts", json={"owner_name": "Alice", "starting_balance": "1000.00"}).json()
    bob = client.post("/accounts", json={"owner_name": "Bob", "starting_balance": "500.00"}).json()
    
    client.post("/transactions", json={
        "sender_id": alice["id"],
        "receiver_id": bob["id"],
        "amount": "200.00"
    }, headers={"Idempotency-Key": str(uuid.uuid4())})
    
    alice_ledger = client.get(f"/accounts/{alice['id']}/ledger").json()
    bob_ledger = client.get(f"/accounts/{bob['id']}/ledger").json()
    
    assert len(alice_ledger["items"]) == 1
    assert alice_ledger["items"][0]["entry_type"] == "DEBIT"
    assert alice_ledger["items"][0]["amount"] == "200.00"
    
    assert len(bob_ledger["items"]) == 1
    assert bob_ledger["items"][0]["entry_type"] == "CREDIT"
    assert bob_ledger["items"][0]["amount"] == "200.00"

def test_sender_not_found(client):
    resp = client.post("/transactions", json={
        "sender_id": str(uuid.uuid4()),
        "receiver_id": str(uuid.uuid4()),
        "amount": "10.00"
    }, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert resp.status_code == 404
    assert "Sender" in resp.json()["detail"]

def test_receiver_not_found(client):
    alice = client.post("/accounts", json={"owner_name": "Alice", "starting_balance": "1000.00"}).json()
    resp = client.post("/transactions", json={
        "sender_id": alice["id"],
        "receiver_id": str(uuid.uuid4()),
        "amount": "10.00"
    }, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert resp.status_code == 404
    assert "Receiver" in resp.json()["detail"]

def test_ledger_pagination(client):
    alice = client.post("/accounts", json={"owner_name": "Alice", "starting_balance": "1000.00"}).json()
    bob = client.post("/accounts", json={"owner_name": "Bob", "starting_balance": "500.00"}).json()
    
    client.post("/transactions", json={
        "sender_id": alice["id"],
        "receiver_id": bob["id"],
        "amount": "100.00"
    }, headers={"Idempotency-Key": str(uuid.uuid4())})
    client.post("/transactions", json={
        "sender_id": alice["id"],
        "receiver_id": bob["id"],
        "amount": "50.00"
    }, headers={"Idempotency-Key": str(uuid.uuid4())})
    
    resp = client.get(f"/accounts/{alice['id']}/ledger?page=1&size=1")
    data = resp.json()
    assert data["page"] == 1
    assert data["size"] == 1
    assert data["total"] == 2
    assert len(data["items"]) == 1
    
    resp2 = client.get(f"/accounts/{alice['id']}/ledger?page=2&size=1")
    data2 = resp2.json()
    assert data2["page"] == 2
    assert len(data2["items"]) == 1
    assert data2["items"][0]["id"] != data["items"][0]["id"]

def test_transaction_not_found(client):
    resp = client.get(f"/transactions/{uuid.uuid4()}")
    assert resp.status_code == 404
