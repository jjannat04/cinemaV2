import httpx

# Test payment with mock mode
# First get a seat
movies = httpx.get('http://localhost:8000/movies').json()
showtimes = httpx.get(f'http://localhost:8000/movies/{movies[0]["id"]}/showtimes').json()
seats = httpx.get(f'http://localhost:8000/seats/{showtimes[0]["id"]}').json()
available = [s for s in seats['seats'] if s['status'] == 'available']
seat = available[0]

# Hold seat
hold = httpx.post(f'http://localhost:8000/seats/{showtimes[0]["id"]}/hold', 
                json={'seat_id': seat['id'], 'user_identifier': 'mock_test'})
print(f'Hold: {hold.status_code}')

if hold.status_code == 201:
    hold_id = hold.json()['hold_id']
    # Try payment (currently in real gateway mode, should fail without gateway)
    try:
        payment = httpx.post(f'http://localhost:8000/bookings/{hold_id}/pay',
                            json={'hold_id': hold_id, 'phone': '01700000000', 
                                  'callback_url': 'http://app:8000/bookings/callback'},
                            timeout=10)
        print(f'Payment: {payment.status_code}')
        print(f'Response: {payment.text}')
    except Exception as e:
        print(f'Payment error: {e}')