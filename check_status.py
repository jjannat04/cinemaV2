import httpx

# Check booking status
booking = httpx.get('http://localhost:8000/bookings/1').json()
print(f'Booking status: {booking["status"]}')

# Check seat status
seats = httpx.get('http://localhost:8000/seats/1').json()
print(f'Total seats: {len(seats["seats"])}')
print(f'Seats available: {len([s for s in seats["seats"] if s["status"] == "available"])}')
print(f'Seats held: {len([s for s in seats["seats"] if s["status"] == "held"])}')
print(f'Seats booked: {len([s for s in seats["seats"] if s["status"] == "booked"])}')