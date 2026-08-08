import requests
import json

BASE_URL = "http://localhost:8000"

# 1. Hold a seat
print("1. Holding seat...")
hold = requests.post(f"{BASE_URL}/seats/1/hold", json={"seat_id": 1, "user_identifier": "payment_test"})
print(f"Hold status: {hold.status_code}")
if hold.status_code == 201:
    hold_data = hold.json()
    hold_id = hold_data['hold_id']
    print(f"Hold ID: {hold_id}")
else:
    print(f"Hold failed: {hold.text}")
    exit(1)

# 2. Try to pay
print("\n2. Initiating payment...")
callback_url = "http://app:8000/bookings/callback"
payment = requests.post(f"{BASE_URL}/bookings/{hold_id}/pay", json={"hold_id": hold_id, "phone": "01700000000", "callback_url": callback_url})
print(f"Payment status: {payment.status_code}")
print(f"Payment response: {payment.text}")

# 3. Check gateway
print("\n3. Checking gateway...")
try:
    gateway_health = requests.get("http://localhost:9000/health", timeout=5)
    print(f"Gateway health: {gateway_health.status_code}")
    print(f"Gateway response: {gateway_health.text}")
except Exception as e:
    print(f"Gateway error: {e}")