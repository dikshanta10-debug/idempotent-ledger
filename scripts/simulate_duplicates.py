import requests
import uuid
import time

BASE_URL = "http://localhost:8000"

# Create accounts
alice = requests.post(f"{BASE_URL}/accounts", json={
    "owner_name": "Alice", "starting_balance": "100000.00"
}).json()
bob = requests.post(f"{BASE_URL}/accounts", json={
    "owner_name": "Bob", "starting_balance": "50000.00"
}).json()

key = str(uuid.uuid4())
payload = {
    "sender_id": alice["id"],
    "receiver_id": bob["id"],
    "amount": "10.00"
}
headers = {"Idempotency-Key": key}

# Send 10,000 identical requests
responses = []
start = time.time()
for i in range(10000):
    r = requests.post(f"{BASE_URL}/transactions", json=payload, headers=headers)
    responses.append(r.json())
    if i % 1000 == 0:
        print(f"Sent {i} requests...")

elapsed = time.time() - start

# All responses must be identical
first = responses[0]
all_identical = all(r == first for r in responses)

# Check DB has exactly 1 transaction
txn_id = first["id"]
txn_resp = requests.get(f"{BASE_URL}/transactions/{txn_id}")
assert txn_resp.status_code == 200

alice_after = requests.get(f"{BASE_URL}/accounts/{alice['id']}").json()
bob_after = requests.get(f"{BASE_URL}/accounts/{bob['id']}").json()

print(f"\nResults:")
print(f"Total requests: {len(responses)}")
print(f"All identical: {all_identical}")
print(f"Alice balance: {alice_after['balance']} (expected 99990.00)")
print(f"Bob balance: {bob_after['balance']} (expected 50010.00)")
print(f"Time: {elapsed:.2f}s")
print(f"Throughput: {len(responses)/elapsed:.0f} req/s")
print(f"DUPLICATES: ZERO" if all_identical and alice_after["balance"] == "99990.00" else "FAILED")
