"""
Simple concurrency test - tests with 10 concurrent requests first
"""
import asyncio
import aiohttp
import time

# Change this to your Render URL
BASE_URL = "https://cinemaseat.onrender.com"  # Updated with your actual URL
# BASE_URL = "http://localhost:8000"
async def test_concurrent_holds():
    """Test with 10 concurrent requests"""
    print("Testing with 10 concurrent hold requests...")
    
    async with aiohttp.ClientSession() as session:
        # Get showtime and seat
        async with session.get(f"{BASE_URL}/movies") as resp:
            movies = await resp.json()
        movie_id = movies[0]['id']
        
        async with session.get(f"{BASE_URL}/movies/{movie_id}/showtimes") as resp:
            showtimes = await resp.json()
        showtime_id = showtimes[0]['id']
        
        async with session.get(f"{BASE_URL}/seats/{showtime_id}") as resp:
            seats_data = await resp.json()
        
        available_seats = [s for s in seats_data['seats'] if s['status'] == 'available']
        if not available_seats:
            print("No available seats!")
            return
        
        target_seat = available_seats[0]
        seat_id = target_seat['id']
        seat_info = f"{target_seat['row_letter']}{target_seat['seat_number']}"
        
        print(f"Target: Seat {seat_info} (ID: {seat_id})")
        
        # Fire 10 concurrent requests
        start_time = time.time()
        results = {'success': 0, 'conflict': 0, 'error': 0}
        
        async def single_hold_request(user_id):
            try:
                async with session.post(
                    f"{BASE_URL}/seats/{showtime_id}/hold",
                    json={
                        "seat_id": seat_id,
                        "user_identifier": f"user_{user_id}"
                    }
                ) as resp:
                    if resp.status == 201:
                        results['success'] += 1
                    elif resp.status == 409:
                        results['conflict'] += 1
                    else:
                        results['error'] += 1
                        print(f"User {user_id}: Status {resp.status}")
            except Exception as e:
                results['error'] += 1
                print(f"User {user_id}: Error {e}")
        
        # Create 10 concurrent tasks
        tasks = []
        for i in range(10):
            tasks.append(single_hold_request(i))
        
        # Execute all concurrently
        await asyncio.gather(*tasks)
        
        elapsed = time.time() - start_time
        
        # Verify final state
        async with session.get(f"{BASE_URL}/seats/{showtime_id}") as resp:
            final_seats = await resp.json()
        
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
        else:
            print(f"  FAIL: Expected 1 success, 9 conflicts")
            print(f"  Oversell count: {max(0, results['success'] - 1)}")

if __name__ == "__main__":
    asyncio.run(test_concurrent_holds())