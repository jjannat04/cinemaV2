import httpx

# Check booking status
booking = httpx.get('http://localhost:8000/bookings/1').json()
print(f'Booking status: {booking["status"]}')

# Check seat status
seats = httpx.get('http://localhost:8000/seats/1').json()
seat = next((s for s in seats['seats'] if s['id'] == 361), None)
print(f'Seat status: {seat["status"] if seat else "UNKNOWN"}')