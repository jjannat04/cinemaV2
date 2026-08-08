"""
Synchronous concurrency test using regular requests
Tests concurrency control without async complications
"""
import requests
import time
import threading

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health check"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Health Check: {response.status_code} - {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health Check Failed: {e}")
        return False

def test_concurrent_holds():
    """Test with 10 concurrent requests using threads"""
    print("=" * 60)
    print("Testing 10 Concurrent Hold Requests")
    print("=" * 60)
    
    # Get showtime and seat
    try:
        movies = requests.get(f"{BASE_URL}/movies", timeout=5).json()
        movie_id = movies[0]['id']
        
        showtimes = requests.get(f"{BASE_URL}/movies/{movie_id}/showtimes", timeout=5).json()
        showtime_id = showtimes[0]['id']
        
        seats_data = requests.get(f"{BASE_URL}/seats/{showtime_id}", timeout=5).json()
        available_seats = [s for s in seats_data['seats'] if s['status'] == 'available']
        
        if not available_seats:
            print("No available seats!")
            return
        
        target_seat = available_seats[0]
        seat_id = target_seat['id']
        seat_info = f"{target_seat['row_letter']}{target_seat['seat_number']}"
        
        print(f"Target: Seat {seat_info} (ID: {seat_id})")
        print(f"Firing 10 concurrent requests...")
        
        results = {'success': 0, 'conflict': 0, 'error': 0}
        lock = threading.Lock()
        
        def single_hold(user_id):
            try:
                response = requests.post(
                    f"{BASE_URL}/seats/{showtime_id}/hold",
                    json={
                        "seat_id": seat_id,
                        "user_identifier": f"user_{user_id}"
                    },
                    timeout=10
                )
                
                with lock:
                    if response.status_code == 201:
                        results['success'] += 1
                    elif response.status_code == 409:
                        results['conflict'] += 1
                    else:
                        results['error'] += 1
                        print(f"User {user_id}: Status {response.status_code}")
            except Exception as e:
                with lock:
                    results['error'] += 1
                    print(f"User {user_id}: Error {e}")
        
        # Create and start 10 threads
        threads = []
        start_time = time.time()
        
        for i in range(10):
            thread = threading.Thread(target=single_hold, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        elapsed = time.time() - start_time
        
        # Verify final state
        final_seats = requests.get(f"{BASE_URL}/seats/{showtime_id}", timeout=5).json()
        final_seat = next((s for s in final_seats['seats'] if s['id'] == seat_id), None)
        
        # Report results
        print(f"\nResults:")
        print(f"  Requests sent: 10")
        print(f"  Successful holds: {results['success']}")
        print(f"  Rejected (conflict): {results['conflict']}")
        print(f"  Errors: {results['error']}")
        print(f"  Time elapsed: {elapsed:.2f}s")
        print(f"  Final seat status: {final_seat['status'] if final_seat else 'UNKNOWN'}")
        
        # Check for oversell
        if results['success'] == 1 and results['conflict'] == 9:
            print(f"  PASS: Exactly 1 success, 9 conflicts - NO OVERSELL")
            return True
        else:
            print(f"  FAIL: Expected 1 success, 9 conflicts")
            print(f"  Oversell count: {max(0, results['success'] - 1)}")
            return False
            
    except Exception as e:
        print(f"Test failed: {e}")
        return False

def main():
    print("Synchronous Concurrency Test")
    print(f"Target: {BASE_URL}")
    print(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test health first
    if not test_health():
        print("Health check failed. Stopping.")
        return
    
    # Test concurrency
    success = test_concurrent_holds()
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Concurrent Holds: {'PASS' if success else 'FAIL'}")
    print(f"Completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()