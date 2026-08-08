from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
from app.database import get_db_context
from app.models import SeatHold, Seat, SeatStatus
import logging

logger = logging.getLogger(__name__)

def cleanup_expired_holds():
    """
    Background task to clean up expired holds and release seats.
    
    This should be run periodically (e.g., every minute).
    """
    try:
        with get_db_context() as db:
            # Find all expired holds that are still active
            expired_holds = db.execute(
                select(SeatHold).where(
                    SeatHold.is_active == True,
                    SeatHold.hold_expires_at < datetime.utcnow()
                )
            ).scalars().all()
            
            for hold in expired_holds:
                # Deactivate the hold
                hold.is_active = False
                
                # Release the seat back to available
                seat = db.execute(
                    select(Seat).where(Seat.id == hold.seat_id)
                ).scalar_one_or_none()
                
                if seat and seat.status == SeatStatus.HELD:
                    seat.status = SeatStatus.AVAILABLE
                    logger.info(f"Released seat {seat.id} from expired hold {hold.id}")
                
            db.commit()
            
            if expired_holds:
                logger.info(f"Cleaned up {len(expired_holds)} expired holds")
                
    except Exception as e:
        logger.error(f"Error cleaning up expired holds: {str(e)}")

def start_cleanup_scheduler():
    """
    Start a background scheduler to periodically clean up expired holds.
    
    For production, consider using Celery or a dedicated task queue.
    For this hackathon, we'll use a simple periodic task.
    """
    import threading
    import time
    
    def run_periodic():
        while True:
            try:
                cleanup_expired_holds()
                time.sleep(30)  # Run every 30 seconds
            except Exception as e:
                logger.error(f"Scheduler error: {str(e)}")
                time.sleep(30)
    
    # Start in background thread
    thread = threading.Thread(target=run_periodic, daemon=True)
    thread.start()
    logger.info("Started hold cleanup scheduler")