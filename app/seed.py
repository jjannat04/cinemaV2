from datetime import datetime, timedelta
from app.database import get_db_context
from app.models import Movie, Theatre, Showtime, Seat, SeatStatus, SeatHold, Booking

def seed_database(force=False):
    """Populate database with sample data"""
    with get_db_context() as db:
        # Check if data already exists (check for movies)
        if not force and db.query(Movie).count() > 0:
            print("Database already seeded. Skipping.")
            return
        
        # Clear existing data to ensure clean state
        db.query(Seat).delete()
        db.query(SeatHold).delete()
        db.query(Booking).delete()
        db.query(Showtime).delete()
        db.query(Theatre).delete()
        db.query(Movie).delete()
        db.commit()
        
        # Create movies
        movie1 = Movie(
            title="Spider-Man: Brand New Day",
            description="The latest Spider-Man adventure",
            duration_minutes=150
        )
        movie2 = Movie(
            title="The Dark Knight",
            description="Batman faces the Joker",
            duration_minutes=152
        )
        db.add_all([movie1, movie2])
        db.flush()
        
        # Create theatre
        theatre = Theatre(
            name="Main Hall",
            total_rows=10,
            seats_per_row=12
        )
        db.add(theatre)
        db.flush()
        
        # Create showtimes (starting tomorrow)
        tomorrow = datetime.utcnow() + timedelta(days=1)
        showtime1 = Showtime(
            movie_id=movie1.id,
            theatre_id=theatre.id,
            start_time=tomorrow.replace(hour=20, minute=0),  # 8 PM
            price=15.00
        )
        showtime2 = Showtime(
            movie_id=movie1.id,
            theatre_id=theatre.id,
            start_time=tomorrow.replace(hour=23, minute=0),  # 11 PM (midnight premiere)
            price=18.00
        )
        showtime3 = Showtime(
            movie_id=movie2.id,
            theatre_id=theatre.id,
            start_time=tomorrow.replace(hour=18, minute=0),  # 6 PM
            price=12.00
        )
        db.add_all([showtime1, showtime2, showtime3])
        db.flush()
        
        # Create seats for each showtime
        for showtime in [showtime1, showtime2, showtime3]:
            for row_num in range(theatre.total_rows):
                row_letter = chr(ord('A') + row_num)
                for seat_num in range(1, theatre.seats_per_row + 1):
                    seat = Seat(
                        showtime_id=showtime.id,
                        row_letter=row_letter,
                        seat_number=seat_num,
                        status=SeatStatus.AVAILABLE,
                        price=showtime.price
                    )
                    db.add(seat)
        
        db.commit()
        print(f"Database seeded successfully!")
        print(f"- Movies: {db.query(Movie).count()}")
        print(f"- Theatres: {db.query(Theatre).count()}")
        print(f"- Showtimes: {db.query(Showtime).count()}")
        print(f"- Seats: {db.query(Seat).count()}")

if __name__ == "__main__":
    seed_database()