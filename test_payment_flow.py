"""
Step-by-step payment flow test
"""
import requests
import time

BASE_URL = "http://localhost:8000"
GATEWAY_URL = "asifmahmoud414/mock-gateway:latest"

print("Testing Payment Flow")
print("=" * 60)

# Step 1: Get a seat to hold
print("\nStep 1: Get showtime and seat")
movies = requests.get(f"{BASE_URL}/movies", timeout=5).json()
movie_id = movies[0]['id']
showtimes = requests.get(f"{BASE_URL}/movies/{movie_id}/showtimes", timeout=5).json()
showtime_id = showtimes[0]['id']
seats = requests.get(f"{BASE_URL}/seats/{showtime_id}", timeout=5).json()
available_seats = [s for s in seats['seats'] if s['status'] == 'available']

if not available_seats:
    print("No available seats!")
    exit(1)

seat = available_seats[0]
seat_id = seat['id']
seat_info = f"{seat['row_letter']}{seat['seat_number']}"
print(f"Selected seat: {seat_info} (ID: {seat_id})")

# Step 2: Hold the seat
print("\nStep 2: Hold the seat")
hold_response = requests.post(
    f"{BASE_URL}/seats/{showtime_id}/hold",
    json={"seat_id": seat_id, "user_identifier": "test_user_payment"},
    timeout=10
)

if hold_response.status_code == 201:
    hold_data = hold_response.json()
    hold_id = hold_data['hold_id']
    print(f"✅ Seat held successfully")
    print(f"   Hold ID: {hold_id}")
    print(f"   Expires: {hold_data['hold_expires_at']}")
else:
    print(f"❌ Hold failed: {hold_response.status_code}")
    print(hold_response.text)
    exit(1)

# Step 3: Initiate payment
print("\nStep 3: Initiate payment")
callback_url = "http://app:8000/bookings/callback"  # Docker service name

payment_response = requests.post(
    f"{BASE_URL}/bookings/{hold_id}/pay",
    json={
        "hold_id": hold_id,
        "phone": "01700000000",
        "callback_url": callback_url
    },
    timeout=15
)

if payment_response.status_code == 202:
    payment_data = payment_response.json()
    booking_id = payment_data['booking_id']
    payment_id = payment_data['payment_id']
    print(f"✅ Payment initiated")
    print(f"   Booking ID: {booking_id}")
    print(f"   Payment ID: {payment_id}")
else:
    print(f"❌ Payment initiation failed: {payment_response.status_code}")
    print(payment_response.text)
    exit(1)

# Step 4: Check gateway debug
print("\nStep 4: Check gateway callback status")
time.sleep(3)  # Wait for callback

try:
    gateway_debug = requests.get(f"{GATEWAY_URL}/debug/deliveries", timeout=5).json()
    print(f"Gateway deliveries: {gateway_debug.get('count', 0)}")
    
    if gateway_debug.get('count', 0) > 0:
        latest = gateway_debug['deliveries'][-1]
        print(f"Latest delivery:")
        print(f"  URL: {latest.get('url')}")
        print(f"  Status: {latest.get('http_status')}")
        print(f"  OK: {latest.get('ok')}")
        print(f"  Error: {latest.get('error', 'None')}")
    else:
        print("No callbacks delivered yet")
except Exception as e:
    print(f"Gateway debug error: {e}")

# Step 5: Check booking status
print("\nStep 5: Check booking status")
booking_status = requests.get(f"{BASE_URL}/bookings/{booking_id}", timeout=5).json()
print(f"Booking status: {booking_status['status']}")

# Step 6: Check seat status
print("\nStep 6: Check seat status")
final_seats = requests.get(f"{BASE_URL}/seats/{showtime_id}", timeout=5).json()
final_seat = next((s for s in final_seats['seats'] if s['id'] == seat_id), None)
print(f"Seat status: {final_seat['status'] if final_seat else 'UNKNOWN'}")

print("\n" + "=" * 60)
print("Payment Flow Test Complete")
print("=" * 60)