import requests
import time
import json

# Test the payment flow
API_BASE = "http://localhost:8000"
GATEWAY_BASE = "http://localhost:9000"

print("Testing CinemaSeat Payment Flow")
print("=" * 50)

# Step 1: Get movies
print("\n1. Getting movies...")
response = requests.get(f"{API_BASE}/movies")
movies = response.json()
print(f"Found {len(movies)} movies")
print(f"First movie: {movies[0]['title']}")

# Step 2: Get showtimes for first movie
print("\n2. Getting showtimes...")
movie_id = movies[0]['id']
response = requests.get(f"{API_BASE}/movies/{movie_id}/showtimes")
showtimes = response.json()
print(f"Found {len(showtimes)} showtimes")
showtime_id = showtimes[0]['id']
print(f"Using showtime {showtime_id}")

# Step 3: Get seats
print("\n3. Getting seats...")
response = requests.get(f"{API_BASE}/seats/{showtime_id}")
seats_data = response.json()
seats = seats_data['seats']
print(f"Found {len(seats)} seats")
available_seats = [s for s in seats if s['status'] == 'available']
print(f"Available seats: {len(available_seats)}")

if available_seats:
    seat_id = available_seats[0]['id']
    seat_info = f"{available_seats[0]['row_letter']}{available_seats[0]['seat_number']}"
    print(f"Selecting seat {seat_info} (ID: {seat_id})")
    
    # Step 4: Hold the seat
    print("\n4. Holding seat...")
    user_id = "test_user_123"
    hold_response = requests.post(
        f"{API_BASE}/seats/{showtime_id}/hold",
        json={
            "seat_id": seat_id,
            "user_identifier": user_id
        }
    )
    
    if hold_response.status_code == 201:
        hold_data = hold_response.json()
        print(f"[OK] Seat held successfully!")
        print(f"  Hold ID: {hold_data['hold_id']}")
        print(f"  Expires at: {hold_data['hold_expires_at']}")
        
        hold_id = hold_data['hold_id']
        
        # Step 5: Initiate payment
        print("\n5. Initiating payment...")
        # IMPORTANT: Use Docker service name "app" instead of localhost
        callback_url = "http://app:8000/bookings/callback"
        
        payment_response = requests.post(
            f"{API_BASE}/bookings/{hold_id}/pay",
            json={
                "hold_id": hold_id,
                "phone": "01700000000",
                "callback_url": callback_url
            }
        )
        
        if payment_response.status_code == 202:
            payment_data = payment_response.json()
            print(f"[OK] Payment initiated successfully!")
            print(f"  Booking ID: {payment_data['booking_id']}")
            print(f"  Payment ID: {payment_data['payment_id']}")
            
            # Step 6: Check gateway debug
            print("\n6. Checking gateway debug...")
            time.sleep(3)  # Wait for callback
            
            debug_response = requests.get(f"{GATEWAY_BASE}/debug/deliveries")
            deliveries = debug_response.json()
            print(f"Gateway deliveries: {len(deliveries)}")
            
            if deliveries:
                latest_delivery = deliveries[-1]
                print(f"Latest delivery:")
                print(f"  Booking ref: {latest_delivery.get('booking_ref')}")
                print(f"  Status: {latest_delivery.get('http_status')}")
                print(f"  Error: {latest_delivery.get('error', 'None')}")
            
            # Step 7: Check booking status
            print("\n7. Checking booking status...")
            booking_response = requests.get(f"{API_BASE}/bookings/{payment_data['booking_id']}")
            booking = booking_response.json()
            print(f"Booking status: {booking['status']}")
            
            # Step 8: Check seat status
            print("\n8. Checking seat status...")
            seat_response = requests.get(f"{API_BASE}/seats/{showtime_id}")
            updated_seats = seat_response.json()['seats']
            updated_seat = next((s for s in updated_seats if s['id'] == seat_id), None)
            if updated_seat:
                print(f"Seat {seat_info} status: {updated_seat['status']}")
            
        else:
            print(f"[FAIL] Payment initiation failed: {payment_response.status_code}")
            print(payment_response.text)
    else:
        print(f"[FAIL] Seat hold failed: {hold_response.status_code}")
        print(hold_response.text)
else:
    print("No available seats to test!")

print("\n" + "=" * 50)
print("Test completed!")