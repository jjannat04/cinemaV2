"""
Milestone 4 Load Testing Script
Tests Scenario A and B as per hackathon requirements
"""
import asyncio
import aiohttp
import time
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"  # Change to deployed URL for real testing

async def scenario_a_concurrent_holds():
    """
    Scenario A: One seat, many buyers
    Fire 100 concurrent hold requests for the exact same seat
    """
    print("=" * 60)
    print("SCENARIO A: One Seat, Many Buyers")
    print("=" * 60)
    
    # Setup: Get a showtime and seat
    async with aiohttp.ClientSession() as session:
        # Get movies
        async with session.get(f"{BASE_URL}/movies") as resp:
            if resp.status != 200:
                print(f"Failed to get movies: {resp.status}")
                print(f"Response: {await resp.text()}")
                return
            movies = await resp.json()
        movie_id = movies[0]['id']
        
        # Get showtimes
        async with session.get(f"{BASE_URL}/movies/{movie_id}/showtimes") as resp:
            showtimes = await resp.json()
        showtime_id = showtimes[0]['id']
        
        # Get seats
        async with session.get(f"{BASE_URL}/seats/{showtime_id}") as resp:
            seats_data = await resp.json()
        
        # Find an available seat
        available_seats = [s for s in seats_data['seats'] if s['status'] == 'available']
        if not available_seats:
            print("No available seats! Reset database first.")
            return
        
        target_seat = available_seats[0]
        seat_id = target_seat['id']
        seat_info = f"{target_seat['row_letter']}{target_seat['seat_number']}"
        
        print(f"Target: Showtime {showtime_id}, Seat {seat_info} (ID: {seat_id})")
        print(f"Firing 100 concurrent hold requests...")
        
        # Fire 100 concurrent requests
        start_time = time.time()
        tasks = []
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
            except Exception as e:
                results['error'] += 1
        
        # Create 100 concurrent tasks
        for i in range(100):
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
        print(f"  Requests sent: 100")
        print(f"  Successful holds: {results['success']}")
        print(f"  Rejected (conflict): {results['conflict']}")
        print(f"  Errors: {results['error']}")
        print(f"  Time elapsed: {elapsed:.2f}s")
        print(f"  Final seat status: {final_seat['status'] if final_seat else 'UNKNOWN'}")
        
        # Check for oversell
        if results['success'] == 1 and results['conflict'] == 99:
            print(f"  ✅ PASS: Exactly 1 success, 99 conflicts - NO OVERSELL")
        else:
            print(f"  ❌ FAIL: Expected 1 success, 99 conflicts")
            print(f"  Oversell count: {max(0, results['success'] - 1)}")

async def scenario_b_hold_expiration():
    """
    Scenario B: The abandoned hold
    Hold a seat and wait for it to expire, then book with different user
    """
    print("\n" + "=" * 60)
    print("SCENARIO B: The Abandoned Hold")
    print("=" * 60)
    
    # Temporarily set short TTL for testing
    print("Note: Set HOLD_TTL_SECONDS=10 for this test")
    print("Restart containers with HOLD_TTL_SECONDS=10 to test properly")
    
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
        
        # User 1 holds the seat
        print(f"\nStep 1: User 1 holds seat...")
        async with session.post(
            f"{BASE_URL}/seats/{showtime_id}/hold",
            json={"seat_id": seat_id, "user_identifier": "user_1"}
        ) as resp:
            if resp.status == 201:
                hold_data = await resp.json()
                print(f"  ✅ Seat held by user_1")
                print(f"  Hold ID: {hold_data['hold_id']}")
                print(f"  Expires at: {hold_data['hold_expires_at']}")
            else:
                print(f"  ❌ Hold failed: {resp.status}")
                return
        
        # Wait for expiration (should be configured to 10 seconds)
        print(f"\nStep 2: Waiting for hold to expire (10 seconds)...")
        await asyncio.sleep(12)  # Wait slightly longer than TTL
        
        # Check seat status
        async with session.get(f"{BASE_URL}/seats/{showtime_id}") as resp:
            seats_after = await resp.json()
        
        seat_after = next((s for s in seats_after['seats'] if s['id'] == seat_id), None)
        print(f"  Seat status after expiration: {seat_after['status'] if seat_after else 'UNKNOWN'}")
        
        if seat_after and seat_after['status'] == 'available':
            print(f"  ✅ Seat returned to available")
            
            # User 2 tries to hold the same seat
            print(f"\nStep 3: User 2 tries to hold the same seat...")
            async with session.post(
                f"{BASE_URL}/seats/{showtime_id}/hold",
                json={"seat_id": seat_id, "user_identifier": "user_2"}
            ) as resp:
                if resp.status == 201:
                    print(f"  ✅ User 2 successfully held the seat")
                    print(f"  Timeline: Hold expired → Seat available → User 2 held")
                else:
                    print(f"  ❌ User 2 failed to hold: {resp.status}")
        else:
            print(f"  ❌ Seat did not return to available")

async def main():
    """Run all scenarios"""
    print(f"Starting load tests at {datetime.now()}")
    print(f"Target: {BASE_URL}")
    print()
    
    # Run Scenario A
    await scenario_a_concurrent_holds()
    
    # Run Scenario B
    await scenario_b_hold_expiration()
    
    print("\n" + "=" * 60)
    print("Load testing complete!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())