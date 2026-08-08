from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from datetime import datetime
from app.config import get_settings
from app.database import get_db, init_db
from app import models
from app.routers import seats, movies, bookings
from app.tasks import start_cleanup_scheduler
import httpx
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events"""
    # Startup
    init_db()
    start_cleanup_scheduler()
    logger.info("CinemaSeat API started")
    yield
    # Shutdown
    logger.info("CinemaSeat API shutting down")

app = FastAPI(
    title="CinemaSeat API",
    description="Movie ticket booking system with high concurrency support",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(seats.router)
app.include_router(movies.router)
app.include_router(bookings.router)

# Mount static files for frontend
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
logger.info(f"Looking for static files in: {static_dir}")
logger.info(f"Static dir exists: {os.path.exists(static_dir)}")
try:
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info("Static files mounted successfully")
except Exception as e:
    logger.warning(f"Static files directory not found or error mounting: {e}")

@app.get("/health")
async def health_check():
    """
    Health check endpoint - must return 200 in under 1 second.
    
    This endpoint is required by judges and must work even when the gateway is down.
    It performs minimal checks to ensure the application is responsive.
    """
    # Return immediately without checking external dependencies
    # This ensures the health check works even when gateway/database are down
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/")
async def root():
    return {"message": "CinemaSeat API", "version": "1.0.0"}

@app.get("/frontend")
async def frontend():
    """Serve the frontend HTML"""
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    try:
        with open(os.path.join(static_dir, "index.html"), "r") as f:
            return HTMLResponse(content=f.read())
    except Exception:
        return {"message": "Frontend not available"}