import requests
import uuid
import time

BASE_URL = "http://localhost:8000"

# Setup accounts
alice = requests.post(f"{BASE_URL}/accounts", json={
    "owner_name": "Alice", "starting_balance": "10000.00"
}).json()
bob = requests.post(f"{BASE_URL}/accounts", json={
    "owner_name": "Bob", "starting_balance": "5000.00"
}).json()

# Measure fresh transaction latency
fresh_times = []
for i in range(100):
    key = str(uuid.uuid4())
    start = time.time()
    requests.post(f"{BASE_URL}/transactions", json={
        "sender_id": alice["id"],
        "receiver_id": bob["id"],
        "amount": "1.00"
    }, headers={"Idempotency-Key": key})
    elapsed = (time.time() - start) * 1000
    fresh_times.append(elapsed)

avg_fresh = sum(fresh_times) / len(fresh_times)
print(f"Fresh transactions (100 samples):")
print(f"  Average latency: {avg_fresh:.1f}ms")
print(f"  Min: {min(fresh_times):.1f}ms, Max: {max(fresh_times):.1f}ms")

# Measure cache-hit latency
cache_key = str(uuid.uuid4())
# First request to cache
requests.post(f"{BASE_URL}/transactions", json={
    "sender_id": alice["id"],
    "receiver_id": bob["id"],
    "amount": "1.00"
}, headers={"Idempotency-Key": cache_key})

cache_times = []
for i in range(100):
    start = time.time()
    requests.post(f"{BASE_URL}/transactions", json={
        "sender_id": alice["id"],
        "receiver_id": bob["id"],
        "amount": "1.00"
    }, headers={"Idempotency-Key": cache_key})
    elapsed = (time.time() - start) * 1000
    cache_times.append(elapsed)

avg_cache = sum(cache_times) / len(cache_times)
print(f"\nCache-hit responses (100 samples):")
print(f"  Average latency: {avg_cache:.1f}ms")
print(f"  Min: {min(cache_times):.1f}ms, Max: {max(cache_times):.1f}ms")
