from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Numeric, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class SeatStatus(enum.Enum):
    AVAILABLE = "available"
    HELD = "held"
    BOOKED = "booked"

class BookingStatus(enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    REFUNDED = "refunded"

class Movie(Base):
    __tablename__ = "movies"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    duration_minutes = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    showtimes = relationship("Showtime", back_populates="movie")

class Theatre(Base):
    __tablename__ = "theatres"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    total_rows = Column(Integer, nullable=False)
    seats_per_row = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    showtimes = relationship("Showtime", back_populates="theatre")

class Showtime(Base):
    __tablename__ = "showtimes"
    
    id = Column(Integer, primary_key=True, index=True)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    theatre_id = Column(Integer, ForeignKey("theatres.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    movie = relationship("Movie", back_populates="showtimes")
    theatre = relationship("Theatre", back_populates="showtimes")
    seats = relationship("Seat", back_populates="showtime")
    bookings = relationship("Booking", back_populates="showtime")
    
    __table_args__ = (
        Index('idx_showtime_start', 'start_time'),
    )

class Seat(Base):
    __tablename__ = "seats"
    
    id = Column(Integer, primary_key=True, index=True)
    showtime_id = Column(Integer, ForeignKey("showtimes.id"), nullable=False)
    row_letter = Column(String, nullable=False)  # e.g., "A", "B", "C"
    seat_number = Column(Integer, nullable=False)  # e.g., 1, 2, 3
    status = Column(Enum(SeatStatus), default=SeatStatus.AVAILABLE, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    
    showtime = relationship("Showtime", back_populates="seats")
    holds = relationship("SeatHold", back_populates="seat")
    
    __table_args__ = (
        Index('idx_seat_showtime_status', 'showtime_id', 'status'),
        Index('idx_seat_unique', 'showtime_id', 'row_letter', 'seat_number', unique=True),
    )

class SeatHold(Base):
    __tablename__ = "seat_holds"
    
    id = Column(Integer, primary_key=True, index=True)
    seat_id = Column(Integer, ForeignKey("seats.id"), nullable=False)
    user_identifier = Column(String, nullable=False)  # session ID or user ID
    hold_started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    hold_expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    seat = relationship("Seat", back_populates="holds")
    booking = relationship("Booking", back_populates="hold", uselist=False)
    
    __table_args__ = (
        Index('idx_hold_expires', 'hold_expires_at'),
        Index('idx_hold_active', 'is_active'),
    )

class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    showtime_id = Column(Integer, ForeignKey("showtimes.id"), nullable=False)
    hold_id = Column(Integer, ForeignKey("seat_holds.id"), nullable=False)
    user_identifier = Column(String, nullable=False)
    payment_id = Column(String, unique=True, nullable=True)  # from gateway
    event_id = Column(String, nullable=True)  # gateway event_id for deduplication
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING, nullable=False)
    callback_received = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    showtime = relationship("Showtime", back_populates="bookings")
    hold = relationship("SeatHold", back_populates="booking")
    
    __table_args__ = (
        Index('idx_booking_payment_id', 'payment_id'),
        Index('idx_booking_event_id', 'event_id'),
        Index('idx_booking_status', 'status'),
    )