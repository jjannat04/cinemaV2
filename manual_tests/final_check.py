import httpx
import json

# Get movies and showtimes
movies = httpx.get('http://localhost:8000/movies').json()
print(f'Movies: {len(movies)}')

movie_id = movies[0]['id']
showtimes = httpx.get(f'http://localhost:8000/movies/{movie_id}/showtimes').json()
print(f'Showtimes: {len(showtimes)}')

showtime_id = showtimes[0]['id']
print(f'Using showtime ID: {showtime_id}')

# Check seats
seats = httpx.get(f'http://localhost:8000/seats/{showtime_id}').json()
print(f'Total seats: {len(seats["seats"])}')
print(f'Available: {len([s for s in seats["seats"] if s["status"] == "available"])}')
print(f'Held: {len([s for s in seats["seats"] if s["status"] == "held"])}')
print(f'Booked: {len([s for s in seats["seats"] if s["status"] == "booked"])}')

# Check booking
booking = httpx.get('http://localhost:8000/bookings/1').json()
print(f'Booking status: {booking["status"]}')