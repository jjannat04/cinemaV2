from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
from app.database import get_db, SessionLocal
from app.models import SeatHold, Booking, Seat, BookingStatus, SeatStatus
from app.schemas import PaymentRequest, PaymentResponse, GatewayCallback, BookingResponse
from app.config import get_settings
import httpx
import logging
import os
import asyncio
import time

router = APIRouter(prefix="/bookings", tags=["bookings"])
settings = get_settings()
logger = logging.getLogger(__name__)

def _release_booking_seat(db: Session, booking: Booking):
    hold = db.execute(
        select(SeatHold).where(SeatHold.id == booking.hold_id)
    ).scalar_one_or_none()
    if not hold:
        return

    seat = db.execute(
        select(Seat).where(Seat.id == hold.seat_id).with_for_update()
    ).scalar_one_or_none()
    if seat and seat.status == SeatStatus.HELD:
        seat.status = SeatStatus.AVAILABLE
    hold.is_active = False

async def _charge_gateway_for_booking(booking_id: int, callback_url: str):
    db = SessionLocal()
    try:
        booking = db.execute(
            select(Booking).where(Booking.id == booking_id)
        ).scalar_one_or_none()
        if not booking or booking.status != BookingStatus.PENDING:
            return

        gateway_url = f"{settings.GATEWAY_URL}/charge"
        payload = {
            "amount": float(booking.amount),
            "currency": "BDT",
            "booking_ref": str(booking.id),
            "callback_url": callback_url
        }
        headers = {}
        if os.getenv("GATEWAY_TEST_MODE") == "deterministic":
            headers["X-Mock-Mode"] = "deterministic"

        async with httpx.AsyncClient() as client:
            response = await client.post(gateway_url, json=payload, headers=headers, timeout=5.0)

        if response.status_code == 202:
            payment_id = response.json().get("payment_id")
            latest = db.execute(
                select(Booking).where(Booking.id == booking_id).with_for_update()
            ).scalar_one_or_none()
            if latest and payment_id and not latest.payment_id:
                latest.payment_id = payment_id
                db.commit()
            return

        latest = db.execute(
            select(Booking).where(Booking.id == booking_id).with_for_update()
        ).scalar_one_or_none()
        if latest and latest.status == BookingStatus.PENDING:
            latest.status = BookingStatus.FAILED
            _release_booking_seat(db, latest)
            db.commit()
    except Exception as e:
        logger.error(f"Gateway charge failed for booking {booking_id}: {str(e)}")
        db.rollback()
        latest = db.execute(
            select(Booking).where(Booking.id == booking_id).with_for_update()
        ).scalar_one_or_none()
        if latest and latest.status == BookingStatus.PENDING and not latest.callback_received:
            latest.status = BookingStatus.FAILED
            _release_booking_seat(db, latest)
            db.commit()
    finally:
        db.close()

@router.post("/{hold_id}/pay", response_model=PaymentResponse, status_code=status.HTTP_202_ACCEPTED)
def initiate_payment(
    hold_id: int,
    request: PaymentRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Initiate payment for a held seat.
    
    This endpoint calls the mock gateway and returns immediately.
    The actual payment confirmation happens via callback.
    """
    # Get the hold with seat lock
    hold = db.execute(
        select(SeatHold).where(
            SeatHold.id == hold_id,
            SeatHold.is_active == True
        ).with_for_update()
    ).scalar_one_or_none()
    
    if not hold:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hold not found or expired"
        )
    
    # Check if hold has expired
    if hold.hold_expires_at < datetime.utcnow():
        hold.is_active = False
        # Release the seat
        seat = db.execute(
            select(Seat).where(Seat.id == hold.seat_id)
        ).scalar_one_or_none()
        if seat:
            seat.status = SeatStatus.AVAILABLE
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hold has expired"
        )
    
    # Check if booking already exists
    existing_booking = db.execute(
        select(Booking).where(Booking.hold_id == hold_id)
    ).scalar_one_or_none()
    
    if existing_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment already initiated for this hold"
        )
    
    # Get seat and showtime information
    seat = db.execute(
        select(Seat).where(Seat.id == hold.seat_id)
    ).scalar_one_or_none()
    
    if not seat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seat not found"
        )
    
    # Create booking record
    booking = Booking(
        showtime_id=seat.showtime_id,
        hold_id=hold_id,
        user_identifier=hold.user_identifier,
        amount=seat.price,
        status=BookingStatus.PENDING
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    
    mock_payment = os.getenv("MOCK_PAYMENT", "false").lower() == "true"
    
    if mock_payment:
        # Mock payment for testing without real gateway
        time.sleep(2)  # Simulate gateway delay
        booking.payment_id = f"mock_pay_{booking.id}"
        booking.status = BookingStatus.CONFIRMED
        seat.status = SeatStatus.BOOKED
        hold.is_active = False
        db.commit()
        
        return PaymentResponse(
            booking_id=booking.id,
            payment_id=booking.payment_id,
            status="confirmed",
            message="Mock payment completed successfully."
        )

    callback_url = request.callback_url
    if "localhost" in callback_url:
        callback_url = callback_url.replace("localhost", "app")
    elif "127.0.0.1" in callback_url:
        callback_url = callback_url.replace("127.0.0.1", "app")

    background_tasks.add_task(_charge_gateway_for_booking, booking.id, callback_url)
    return PaymentResponse(
        booking_id=booking.id,
        payment_id=None,
        status="pending",
        message="Payment accepted. Gateway charge is running in the background."
    )

@router.post("/callback")
def payment_callback(
    callback: GatewayCallback,
    db: Session = Depends(get_db)
):
    """
    Handle payment gateway callback.
    
    This endpoint must be idempotent - handling duplicate callbacks gracefully.
    Always return 200 to prevent gateway retries.
    
    Uses event_id for deduplication as per gateway specification.
    """
    try:
        # Find booking by payment_id. Race-mode callbacks can arrive before
        # /charge returns, so fall back to the booking_ref we supplied.
        booking = db.execute(
            select(Booking).where(Booking.payment_id == callback.payment_id)
        ).scalar_one_or_none()

        if not booking:
            try:
                booking_id = int(callback.booking_ref)
            except ValueError:
                booking_id = None
            if booking_id is not None:
                booking = db.execute(
                    select(Booking).where(Booking.id == booking_id)
                ).scalar_one_or_none()
                if booking and not booking.payment_id:
                    booking.payment_id = callback.payment_id
        
        if not booking:
            logger.warning(f"Callback for unknown payment_id: {callback.payment_id}")
            # Return 200 anyway to prevent retries
            return {"status": "received", "message": "Payment ID not found"}
        
        # Check if callback was already processed using event_id for deduplication
        # Store processed event_ids to handle duplicates properly
        if booking.event_id == callback.event_id:
            logger.info(f"Duplicate callback for payment_id: {callback.payment_id}, event_id: {callback.event_id}")
            return {"status": "received", "message": "Callback already processed"}
        
        # If we have a different event_id for the same payment_id, this is a new callback
        # (edge case: gateway generated new event_id for retry)
        if booking.callback_received and booking.event_id:
            logger.warning(f"New event_id for already processed payment: payment_id={callback.payment_id}, old_event_id={booking.event_id}, new_event_id={callback.event_id}")
            return {"status": "received", "message": "Payment already processed"}
        
        # Process the callback (only if not already processed)
        booking.event_id = callback.event_id  # Store event_id for deduplication
        
        # Only process if not already confirmed/failed
        if booking.status in [BookingStatus.CONFIRMED, BookingStatus.FAILED]:
            logger.info(f"Booking already {booking.status.value}, skipping callback processing")
            return {"status": "received", "message": f"Booking already {booking.status.value}"}
        
        if callback.status == "SUCCEEDED":
            booking.status = BookingStatus.CONFIRMED
            booking.callback_received = True
            
            # Update seat status to booked
            hold = db.execute(
                select(SeatHold).where(SeatHold.id == booking.hold_id)
            ).scalar_one_or_none()
            
            if hold:
                seat = db.execute(
                    select(Seat).where(Seat.id == hold.seat_id)
                ).scalar_one_or_none()
                if seat:
                    seat.status = SeatStatus.BOOKED
                    hold.is_active = False
                    
        elif callback.status == "FAILED":
            booking.status = BookingStatus.FAILED
            booking.callback_received = True
            
            # Release the seat
            _release_booking_seat(db, booking)
                    
        elif callback.status == "REFUNDED":
            booking.status = BookingStatus.REFUNDED
            booking.callback_received = True
            
            # Release the seat
            _release_booking_seat(db, booking)
        
        db.commit()
        
        # Always return 200 to prevent gateway retries
        return {"status": "received", "message": "Callback processed successfully"}
        
    except Exception as e:
        logger.error(f"Callback processing error: {str(e)}")
        
        # Test mode: return 500 to test gateway retry logic
        if os.getenv("TEST_RETRY_LOGIC") == "true":
            return {"status": "error", "message": "Testing retry logic"}, 500
        
        # CRITICAL: Always return 200 to prevent gateway retries
        # Even if processing fails, returning 200 prevents infinite retry loops
        return {"status": "received", "message": "Error processing callback - delivery acknowledged"}

@router.post("/debug/reset")
async def reset_system(db: Session = Depends(get_db)):
    """
    Reset system state for testing.
    Clears all bookings, holds, and resets seat status.
    Also resets gateway state via debug endpoint.
    """
    try:
        # Clear bookings
        db.query(Booking).delete()
        
        # Clear holds
        db.query(SeatHold).delete()
        
        # Reset all seats to available
        seats = db.execute(select(Seat)).scalars().all()
        for seat in seats:
            seat.status = SeatStatus.AVAILABLE
        
        db.commit()
        
        # Try to reset gateway state
        try:
            import httpx
            gateway_reset_url = f"{settings.GATEWAY_URL}/debug/reset"
            async with httpx.AsyncClient() as client:
                await client.post(gateway_reset_url, timeout=5.0)
        except Exception as e:
            logger.warning(f"Gateway reset failed: {e}")
        
        return {"status": "success", "message": "System reset successfully"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"System reset failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="System reset failed"
        )

@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: int, db: Session = Depends(get_db)):
    """Get booking details"""
    booking = db.execute(
        select(Booking).where(Booking.id == booking_id)
    ).scalar_one_or_none()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Get seat_id from hold
    hold = db.execute(
        select(SeatHold).where(SeatHold.id == booking.hold_id)
    ).scalar_one_or_none()
    
    seat_id = hold.seat_id if hold else None
    
    return BookingResponse(
        id=booking.id,
        showtime_id=booking.showtime_id,
        seat_id=seat_id,
        payment_id=booking.payment_id,
        amount=booking.amount,
        status=booking.status,
        created_at=booking.created_at
    )
