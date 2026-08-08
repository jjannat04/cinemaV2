import requests
import threading
import time

# Test within container
BASE_URL = 'http://localhost:8000'

# Health check
health = requests.get(f'{BASE_URL}/health', timeout=5)
print(f'Health: {health.status_code}')

# Get seat
movies = requests.get(f'{BASE_URL}/movies', timeout=5).json()
movie_id = movies[0]['id']
showtimes = requests.get(f'{BASE_URL}/movies/{movie_id}/showtimes', timeout=5).json()
showtime_id = showtimes[0]['id']
seats = requests.get(f'{BASE_URL}/seats/{showtime_id}', timeout=5).json()
available = [s for s in seats['seats'] if s['status'] == 'available']
seat_id = available[0]['id']
print(f'Testing seat {available[0]["row_letter"]}{available[0]["seat_number"]} (ID: {seat_id})')

# Concurrent test
results = {'success': 0, 'conflict': 0, 'error': 0}
lock = threading.Lock()

def hold(user_id):
    try:
        r = requests.post(f'{BASE_URL}/seats/{showtime_id}/hold', 
                        json={'seat_id': seat_id, 'user_identifier': f'user_{user_id}'}, timeout=10)
        with lock:
            if r.status_code == 201:
                results['success'] += 1
            elif r.status_code == 409:
                results['conflict'] += 1
            else:
                results['error'] += 1
    except Exception as e:
        with lock:
            results['error'] += 1

threads = [threading.Thread(target=hold, args=(i,)) for i in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()

print(f'Results: success={results["success"]}, conflict={results["conflict"]}, error={results["error"]}')
print(f'PASS: {results["success"] == 1 and results["conflict"] == 9}')