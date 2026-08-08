import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, Base
from app.models import Seat, SeatStatus, Showtime, Movie, Theatre, SeatHold
from app.config import get_settings
from datetime import datetime, timedelta
import os

# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Override dependency
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Create test data
    movie = Movie(title="Test Movie", duration_minutes=120)
    theatre = Theatre(name="Test Theatre", total_rows=5, seats_per_row=5)
    db.add_all([movie, theatre])
    db.flush()
    
    showtime = Showtime(
        movie_id=movie.id,
        theatre_id=theatre.id,
        start_time=datetime.utcnow() + timedelta(days=1),
        price=10.00
    )
    db.add(showtime)
    db.flush()
    
    # Create seats
    for row in range(5):
        row_letter = chr(ord('A') + row)
        for seat_num in range(1, 6):
            seat = Seat(
                showtime_id=showtime.id,
                row_letter=row_letter,
                seat_number=seat_num,
                status=SeatStatus.AVAILABLE,
                price=10.00
            )
            db.add(seat)
    
    db.commit()
    
    yield db
    
    db.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db):
    with TestClient(app) as test_client:
        yield test_client

@pytest.mark.asyncio
async def test_concurrent_seat_hold():
    """Test that concurrent holds on the same seat result in only one success"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Create test data
    movie = Movie(title="Test Movie", duration_minutes=120)
    theatre = Theatre(name="Test Theatre", total_rows=1, seats_per_row=1)
    db.add_all([movie, theatre])
    db.flush()
    
    showtime = Showtime(
        movie_id=movie.id,
        theatre_id=theatre.id,
        start_time=datetime.utcnow() + timedelta(days=1),
        price=10.00
    )
    db.add(showtime)
    db.flush()
    
    seat = Seat(
        showtime_id=showtime.id,
        row_letter="A",
        seat_number=1,
        status=SeatStatus.AVAILABLE,
        price=10.00
    )
    db.add(seat)
    db.commit()
    showtime_id = showtime.id
    seat_id = seat.id
    db.close()
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Fire 10 concurrent hold requests for the same seat
        tasks = []
        for i in range(10):
            task = ac.post(
                f"/seats/{showtime_id}/hold",
                json={
                    "seat_id": seat_id,
                    "user_identifier": f"user_{i}"
                }
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Count successes and failures
    successes = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 201)
    conflicts = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 409)
    
    # Exactly one should succeed, rest should be conflicts
    assert successes == 1, f"Expected 1 success, got {successes}"
    assert conflicts == 9, f"Expected 9 conflicts, got {conflicts}"
    
    # Verify seat is held
    db = TestingSessionLocal()
    held_seat = db.query(Seat).filter(Seat.id == seat_id).first()
    assert held_seat.status == SeatStatus.HELD
    db.close()
    
    Base.metadata.drop_all(bind=engine)

@pytest.mark.asyncio
async def test_duplicate_callback():
    """Test that duplicate callbacks are handled idempotently"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Create test data
    movie = Movie(title="Test Movie", duration_minutes=120)
    theatre = Theatre(name="Test Theatre", total_rows=1, seats_per_row=1)
    db.add_all([movie, theatre])
    db.flush()
    
    showtime = Showtime(
        movie_id=movie.id,
        theatre_id=theatre.id,
        start_time=datetime.utcnow() + timedelta(days=1),
        price=10.00
    )
    db.add(showtime)
    db.flush()
    
    seat = Seat(
        showtime_id=showtime.id,
        row_letter="A",
        seat_number=1,
        status=SeatStatus.AVAILABLE,
        price=10.00
    )
    db.add(seat)
    db.flush()
    
    hold = SeatHold(
        seat_id=seat.id,
        user_identifier="test_user",
        hold_started_at=datetime.utcnow(),
        hold_expires_at=datetime.utcnow() + timedelta(minutes=5),
        is_active=True
    )
    db.add(hold)
    db.flush()
    
    from app.models import Booking, BookingStatus
    booking = Booking(
        showtime_id=showtime.id,
        hold_id=hold.id,
        user_identifier="test_user",
        payment_id="pay_test_123",
        amount=10.00,
        status=BookingStatus.PENDING
    )
    db.add(booking)
    db.commit()
    booking_id = booking.id
    seat_id = seat.id
    db.close()
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # First callback
        response1 = await ac.post(
            "/bookings/callback",
            json={
                "event_id": "evt_001",
                "payment_id": "pay_test_123",
                "booking_ref": str(booking_id),
                "status": "SUCCEEDED",
                "amount": 10.00
            }
        )
        
        # Duplicate callback
        response2 = await ac.post(
            "/bookings/callback",
            json={
                "event_id": "evt_001",
                "payment_id": "pay_test_123",
                "booking_ref": str(booking_id),
                "status": "SUCCEEDED",
                "amount": 10.00
            }
        )
    
    # Both should return 200
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    # Verify booking is confirmed
    db = TestingSessionLocal()
    confirmed_booking = db.query(Booking).filter(Booking.id == booking_id).first()
    assert confirmed_booking.status == BookingStatus.CONFIRMED
    assert confirmed_booking.callback_received == True
    
    # Verify seat is booked
    booked_seat = db.query(Seat).filter(Seat.id == seat_id).first()
    assert booked_seat.status == SeatStatus.BOOKED
    db.close()
    
    Base.metadata.drop_all(bind=engine)

def test_health_check(client):
    """Test that health check returns 200 quickly"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_hold_expiration(db, client):
    """Test that expired holds are properly cleaned up"""
    # Get the first seat
    seat = db.query(Seat).first()
    showtime_id = seat.showtime_id
    
    # Create an expired hold
    expired_hold = SeatHold(
        seat_id=seat.id,
        user_identifier="test_user",
        hold_started_at=datetime.utcnow() - timedelta(minutes=10),
        hold_expires_at=datetime.utcnow() - timedelta(minutes=5),
        is_active=True
    )
    db.add(expired_hold)
    
    # Mark seat as held
    seat.status = SeatStatus.HELD
    db.commit()
    
    # Run request-path cleanup against the same test DB session.
    from app.tasks import release_expired_holds_in_session
    release_expired_holds_in_session(db, showtime_id=showtime_id)
    db.commit()
    
    # Verify hold is deactivated and seat is available
    db.refresh(expired_hold)
    db.refresh(seat)
    
    assert expired_hold.is_active == False
    assert seat.status == SeatStatus.AVAILABLE
