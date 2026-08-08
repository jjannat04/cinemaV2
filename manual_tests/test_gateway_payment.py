import httpx
import time

# Test payment flow from inside the container
BASE_URL = 'http://localhost:8000'

print('Testing Payment Flow')
print('=' * 60)

# 1. Get seat
response = httpx.get(f'{BASE_URL}/movies')
movies = response.json()
movie_id = movies[0]['id']
response = httpx.get(f'{BASE_URL}/movies/{movie_id}/showtimes')
showtimes = response.json()
showtime_id = showtimes[0]['id']
response = httpx.get(f'{BASE_URL}/seats/{showtime_id}')
seats = response.json()
available = [s for s in seats['seats'] if s['status'] == 'available']
seat = available[0]
print(f'Target seat: {seat["row_letter"]}{seat["seat_number"]} (ID: {seat["id"]})')

# 2. Hold seat
hold = httpx.post(f'{BASE_URL}/seats/{showtime_id}/hold', 
                    json={'seat_id': seat['id'], 'user_identifier': 'payment_test'})
print(f'Hold status: {hold.status_code}')

if hold.status_code == 201:
    hold_id = hold.json()['hold_id']
    print(f'Hold ID: {hold_id}')
    
    # 3. Initiate payment
    callback_url = 'http://app:8000/bookings/callback'
    payment = httpx.post(f'{BASE_URL}/bookings/{hold_id}/pay',
                            json={'hold_id': hold_id, 'phone': '01700000000', 
                                  'callback_url': callback_url},
                            timeout=15)
    print(f'Payment status: {payment.status_code}')
    print(f'Payment response: {payment.text}')
    
    # 4. Wait and check callback
    time.sleep(5)
    
    # 5. Check booking status
    booking_id = payment.json()['booking_id']
    booking = httpx.get(f'{BASE_URL}/bookings/{booking_id}').json()
    print(f'Booking status: {booking["status"]}')
    
    # 6. Check seat status
    final_seats = httpx.get(f'{BASE_URL}/seats/{showtime_id}').json()
    final_seat = next((s for s in final_seats['seats'] if s['id'] == seat['id']), None)
    print(f'Seat status: {final_seat["status"] if final_seat else "UNKNOWN"}')
    
    # 7. Check gateway debug
    try:
        gateway_debug = httpx.get('http://gateway:9000/debug/deliveries', timeout=5).json()
        print(f'Gateway deliveries: {gateway_debug.get("count", 0)}')
        if gateway_debug.get('count', 0) > 0:
            latest = gateway_debug['deliveries'][-1]
            print(f'Gateway OK: {latest.get("ok")}')
    except Exception as e:
        print(f'Gateway error: {e}')
else:
    print(f'Hold failed: {hold.text}')

print('=' * 60)
print('Payment Flow Test Complete')