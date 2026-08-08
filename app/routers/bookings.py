from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
from app.database import get_db
from app.models import SeatHold, Booking, Seat, BookingStatus, SeatStatus
from app.schemas import PaymentRequest, PaymentResponse, GatewayCallback, BookingResponse
from app.config import get_settings
import httpx
import logging
import os
import asyncio

router = APIRouter(prefix="/bookings", tags=["bookings"])
settings = get_settings()
logger = logging.getLogger(__name__)

@router.post("/{hold_id}/pay", response_model=PaymentResponse, status_code=status.HTTP_202_ACCEPTED)
async def initiate_payment(
    hold_id: int,
    request: PaymentRequest,
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
    
    # Call payment gateway (async, don't wait)
    # Use mock payment if MOCK_PAYMENT environment variable is set
    mock_payment = os.getenv("MOCK_PAYMENT", "false").lower() == "true"
    
    if mock_payment:
        # Mock payment for testing without real gateway
        await asyncio.sleep(2)  # Simulate gateway delay
        booking.payment_id = f"mock_pay_{booking.id}"
        booking.status = BookingStatus.CONFIRMED
        db.commit()
        
        return PaymentResponse(
            booking_id=booking.id,
            payment_id=booking.payment_id,
            status="confirmed",
            message="Mock payment completed successfully."
        )
    
    try:
        gateway_url = f"{settings.GATEWAY_URL}/charge"
        
        # IMPORTANT: callback_url must be reachable from inside the gateway container
        # Use the Docker service name "app" instead of localhost
        # If client sends localhost, replace it with the service name
        callback_url = request.callback_url
        if "localhost" in callback_url:
            callback_url = callback_url.replace("localhost", "app")
        elif "127.0.0.1" in callback_url:
            callback_url = callback_url.replace("127.0.0.1", "app")
        
        payload = {
            "amount": float(seat.price),
            "currency": "BDT",  # Gateway expects BDT currency
            "booking_ref": str(booking.id),
            "callback_url": callback_url
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(gateway_url, json=payload, timeout=5.0)
            
            if response.status_code == 202:
                gateway_data = response.json()
                booking.payment_id = gateway_data.get("payment_id")
                db.commit()
                
                return PaymentResponse(
                    booking_id=booking.id,
                    payment_id=booking.payment_id,
                    status="pending",
                    message="Payment initiated. Waiting for gateway callback."
                )
            else:
                booking.status = BookingStatus.FAILED
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to initiate payment with gateway"
                )
                
    except httpx.TimeoutException:
        booking.status = BookingStatus.FAILED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Gateway timeout"
        )
    except Exception as e:
        booking.status = BookingStatus.FAILED
        db.commit()
        logger.error(f"Payment initiation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during payment initiation"
        )

@router.post("/callback")
async def payment_callback(
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
        # Find booking by payment_id
        booking = db.execute(
            select(Booking).where(Booking.payment_id == callback.payment_id)
        ).scalar_one_or_none()
        
        if not booking:
            logger.warning(f"Callback for unknown payment_id: {callback.payment_id}")
            # Return 200 anyway to prevent retries
            return {"status": "received", "message": "Payment ID not found"}
        
        # Check if callback was already processed using event_id for deduplication
        # Store processed event_ids to handle duplicates properly
        if booking.callback_received:
            logger.info(f"Duplicate callback for payment_id: {callback.payment_id}, event_id: {callback.event_id}")
            return {"status": "received", "message": "Callback already processed"}
        
        # Process the callback
        booking.event_id = callback.event_id  # Store event_id for deduplication
        
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
            hold = db.execute(
                select(SeatHold).where(SeatHold.id == booking.hold_id)
            ).scalar_one_or_none()
            
            if hold:
                seat = db.execute(
                    select(Seat).where(Seat.id == hold.seat_id)
                ).scalar_one_or_none()
                if seat:
                    seat.status = SeatStatus.AVAILABLE
                    hold.is_active = False
                    
        elif callback.status == "REFUNDED":
            booking.status = BookingStatus.REFUNDED
            booking.callback_received = True
            
            # Release the seat
            hold = db.execute(
                select(SeatHold).where(SeatHold.id == booking.hold_id)
            ).scalar_one_or_none()
            
            if hold:
                seat = db.execute(
                    select(Seat).where(Seat.id == hold.seat_id)
                ).scalar_one_or_none()
                if seat:
                    seat.status = SeatStatus.AVAILABLE
                    hold.is_active = False
        
        db.commit()
        
        # Always return 200 to prevent gateway retries
        return {"status": "received", "message": "Callback processed successfully"}
        
    except Exception as e:
        logger.error(f"Callback processing error: {str(e)}")
        # Return 200 anyway to prevent retries
        return {"status": "received", "message": "Error processing callback"}

@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(booking_id: int, db: Session = Depends(get_db)):
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