def test_create_account(client):
    response = client.post("/accounts", json={
        "owner_name": "Alice",
        "starting_balance": "1000.00"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["owner_name"] == "Alice"
    assert data["balance"] == "1000.00"
    assert "id" in data

def test_get_account(client):
    # Create first
    create_resp = client.post("/accounts", json={
        "owner_name": "Bob",
        "starting_balance": "500.00"
    })
    account_id = create_resp.json()["id"]
    
    # Get
    get_resp = client.get(f"/accounts/{account_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["balance"] == "500.00"

def test_get_nonexistent_account(client):
    resp = client.get("/accounts/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404

def test_account_ledger_empty(client):
    create_resp = client.post("/accounts", json={
        "owner_name": "Charlie",
        "starting_balance": "300.00"
    })
    account_id = create_resp.json()["id"]
    ledger_resp = client.get(f"/accounts/{account_id}/ledger")
    assert ledger_resp.status_code == 200
    data = ledger_resp.json()
    assert data["items"] == []
    assert data["total"] == 0
