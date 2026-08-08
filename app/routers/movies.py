from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database import get_db
from app.models import Movie, Showtime
from app.schemas import MovieResponse, ShowtimeResponse

router = APIRouter(prefix="/movies", tags=["movies"])

@router.get("", response_model=list[MovieResponse])
async def get_movies(db: Session = Depends(get_db)):
    """Get all available movies"""
    movies = db.execute(select(Movie)).scalars().all()
    return movies

@router.get("/{movie_id}/showtimes", response_model=list[ShowtimeResponse])
async def get_showtimes(movie_id: int, db: Session = Depends(get_db)):
    """Get all showtimes for a specific movie"""
    # Verify movie exists
    movie = db.execute(
        select(Movie).where(Movie.id == movie_id)
    ).scalar_one_or_none()
    
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found"
        )
    
    # Get showtimes
    showtimes = db.execute(
        select(Showtime).where(Showtime.movie_id == movie_id)
    ).scalars().all()
    
    return showtimes