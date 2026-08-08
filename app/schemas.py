from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from app.models import SeatStatus, BookingStatus

# Movie Schemas
class MovieBase(BaseModel):
    title: str
    description: Optional[str] = None
    duration_minutes: int

class MovieResponse(MovieBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Showtime Schemas
class ShowtimeBase(BaseModel):
    movie_id: int
    theatre_id: int
    start_time: datetime
    price: Decimal

class ShowtimeResponse(ShowtimeBase):
    id: int
    created_at: datetime
    movie: MovieResponse
    
    class Config:
        from_attributes = True

# Seat Schemas
class SeatResponse(BaseModel):
    id: int
    showtime_id: int
    row_letter: str
    seat_number: int
    status: SeatStatus
    price: Decimal
    
    class Config:
        from_attributes = True

class SeatMapResponse(BaseModel):
    showtime_id: int
    movie_title: str
    start_time: datetime
    seats: List[SeatResponse]

# Hold Request/Response
class HoldSeatRequest(BaseModel):
    seat_id: int
    user_identifier: str = Field(..., description="Session ID or user ID")

class HoldSeatResponse(BaseModel):
    hold_id: int
    seat_id: int
    row_letter: str
    seat_number: int
    hold_expires_at: datetime
    status: str

# Payment Request/Response
class PaymentRequest(BaseModel):
    hold_id: int
    phone: str = Field(..., description="User phone number for OTP")
    callback_url: str = Field(..., description="Gateway callback URL")

class PaymentResponse(BaseModel):
    booking_id: int
    payment_id: str
    status: str
    message: str

# Callback Schema (from gateway)
class GatewayCallback(BaseModel):
    event_id: str
    payment_id: str
    booking_ref: str
    status: str  # SUCCEEDED, FAILED, REFUNDED
    amount: Decimal

# Booking Response
class BookingResponse(BaseModel):
    id: int
    showtime_id: int
    seat_id: int
    payment_id: Optional[str]
    amount: Decimal
    status: BookingStatus
    created_at: datetime
    
    class Config:
        from_attributes = True

# Health Response
class HealthResponse(BaseModel):
    status: str
    database: str
    gateway: str