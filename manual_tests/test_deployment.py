"""
Deployment Testing Script for Render
Tests basic functionality and concurrency
"""
import requests
import time
import json

# UPDATE THIS WITH YOUR RENDER URL
RENDER_URL = "https://cinemaseat.onrender.com"  # Updated with your actual URL

def test_health_check():
    """Test 1: Health check"""
    print("=" * 60)
    print("TEST 1: Health Check")
    print("=" * 60)
    
    try:
        start = time.time()
        response = requests.get(f"{RENDER_URL}/health", timeout=5)
        elapsed = time.time() - start
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Time: {elapsed:.3f}s")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200 and elapsed < 1.0:
            print("✅ PASS: Health check returns 200 in under 1 second")
            return True
        else:
            print("❌ FAIL: Health check issue")
            return False
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False

def test_movies():
    """Test 2: Get movies"""
    print("\n" + "=" * 60)
    print("TEST 2: Get Movies")
    print("=" * 60)
    
    try:
        response = requests.get(f"{RENDER_URL}/movies", timeout=5)
        movies = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Movies Found: {len(movies)}")
        
        if len(movies) > 0:
            print(f"First Movie: {movies[0]['title']}")
            print("✅ PASS: Movies endpoint working")
            return movies[0]['id']
        else:
            print("❌ FAIL: No movies found")
            return None
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return None

def test_showtimes(movie_id):
    """Test 3: Get showtimes"""
    print("\n" + "=" * 60)
    print("TEST 3: Get Showtimes")
    print("=" * 60)
    
    try:
        response = requests.get(f"{RENDER_URL}/movies/{movie_id}/showtimes", timeout=5)
        showtimes = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Showtimes Found: {len(showtimes)}")
        
        if len(showtimes) > 0:
            print(f"First Showtime: {showtimes[0]['start_time']}")
            print("✅ PASS: Showtimes endpoint working")
            return showtimes[0]['id']
        else:
            print("❌ FAIL: No showtimes found")
            return None
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return None

def test_seats(showtime_id):
    """Test 4: Get seat map"""
    print("\n" + "=" * 60)
    print("TEST 4: Get Seat Map")
    print("=" * 60)
    
    try:
        response = requests.get(f"{RENDER_URL}/seats/{showtime_id}", timeout=5)
        seats_data = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Movie: {seats_data['movie_title']}")
        print(f"Total Seats: {len(seats_data['seats'])}")
        
        available = [s for s in seats_data['seats'] if s['status'] == 'available']
        print(f"Available Seats: {len(available)}")
        
        if len(available) > 0:
            first_seat = available[0]
            print(f"First Available: {first_seat['row_letter']}{first_seat['seat_number']} (ID: {first_seat['id']})")
            print("✅ PASS: Seat map endpoint working")
            return showtime_id, first_seat['id'], f"{first_seat['row_letter']}{first_seat['seat_number']}"
        else:
            print("❌ FAIL: No available seats")
            return None, None, None
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return None, None, None

def test_hold_seat(showtime_id, seat_id):
    """Test 5: Hold a seat"""
    print("\n" + "=" * 60)
    print("TEST 5: Hold Seat")
    print("=" * 60)
    
    try:
        response = requests.post(
            f"{RENDER_URL}/seats/{showtime_id}/hold",
            json={
                "seat_id": seat_id,
                "user_identifier": "test_user_deployment"
            },
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 201:
            hold_data = response.json()
            print(f"Hold ID: {hold_data['hold_id']}")
            print(f"Expires: {hold_data['hold_expires_at']}")
            print("✅ PASS: Seat hold working")
            return hold_data['hold_id']
        else:
            print(f"Response: {response.text}")
            print("❌ FAIL: Seat hold failed")
            return None
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return None

def test_concurrent_holds(showtime_id, seat_id):
    """Test 6: Concurrent holds (10 requests)"""
    print("\n" + "=" * 60)
    print("TEST 6: Concurrent Holds (10 requests)")
    print("=" * 60)
    
    import concurrent.futures
    
    def single_hold(user_id):
        try:
            response = requests.post(
                f"{RENDER_URL}/seats/{showtime_id}/hold",
                json={
                    "seat_id": seat_id,
                    "user_identifier": f"concurrent_user_{user_id}"
                },
                timeout=10
            )
            return response.status_code
        except Exception as e:
            return 500
    
    print(f"Firing 10 concurrent requests for seat {seat_id}...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(single_hold, i) for i in range(10)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    success = sum(1 for r in results if r == 201)
    conflicts = sum(1 for r in results if r == 409)
    errors = sum(1 for r in results if r not in [201, 409])
    
    print(f"Results:")
    print(f"  Successful: {success}")
    print(f"  Conflicts: {conflicts}")
    print(f"  Errors: {errors}")
    
    if success == 1 and conflicts == 9:
        print("✅ PASS: Exactly 1 success, 9 conflicts - NO OVERSELL")
        return True
    else:
        print(f"❌ FAIL: Expected 1 success, 9 conflicts")
        return False

def main():
    """Run all deployment tests"""
    print(f"Testing Deployed Application")
    print(f"Target: {RENDER_URL}")
    print(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run tests
    health_ok = test_health_check()
    
    if not health_ok:
        print("\n❌ Health check failed. Stopping tests.")
        return
    
    movie_id = test_movies()
    if not movie_id:
        print("\n❌ Movies test failed. Stopping tests.")
        return
    
    showtime_id = test_showtimes(movie_id)
    if not showtime_id:
        print("\n❌ Showtimes test failed. Stopping tests.")
        return
    
    showtime_id, seat_id, seat_info = test_seats(showtime_id)
    if not seat_id:
        print("\n❌ Seats test failed. Stopping tests.")
        return
    
    hold_id = test_hold_seat(showtime_id, seat_id)
    
    # Get a fresh seat for concurrency test
    print("\nGetting fresh seat for concurrency test...")
    response = requests.get(f"{RENDER_URL}/seats/{showtime_id}", timeout=5)
    seats_data = response.json()
    available = [s for s in seats_data['seats'] if s['status'] == 'available']
    
    if available:
        fresh_seat = available[0]
        concurrent_ok = test_concurrent_holds(showtime_id, fresh_seat['id'])
    else:
        print("⚠️  No available seats for concurrency test")
        concurrent_ok = None
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Health Check: {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"Movies: {'✅ PASS' if movie_id else '❌ FAIL'}")
    print(f"Showtimes: {'✅ PASS' if showtime_id else '❌ FAIL'}")
    print(f"Seats: {'✅ PASS' if seat_id else '❌ FAIL'}")
    print(f"Hold Seat: {'✅ PASS' if hold_id else '❌ FAIL'}")
    print(f"Concurrent Holds: {'✅ PASS' if concurrent_ok else '❌ FAIL' if concurrent_ok is False else '⚠️  SKIPPED'}")
    
    print(f"\nTest completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()