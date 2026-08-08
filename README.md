# CinemaSeat - Movie Ticket Booking System

A scalable cinema ticket booking system that handles high concurrency without double-booking seats.

## Tech Stack
- **Backend**: Python + FastAPI
- **Database**: PostgreSQL (with row locks for concurrency control)
- **Payment Gateway**: Mock gateway (asifmahmoud414/mock-gateway:latest)
- **Containerization**: Docker + Docker Compose
- **Testing**: Pytest with async support

## Quick Start

### Prerequisites
- Docker and Docker Compose installed

### Running the Application
```bash
docker-compose up
```

The API will be available at `http://localhost:8000`
The mock gateway will be available at `http://localhost:9000`

### Health Check
```bash
curl http://localhost:8000/health
```

### Frontend
Access the frontend at `http://localhost:8000/frontend`

### Initialize Database with Sample Data
```bash
# After starting the containers, run:
docker-compose exec app python -m app.seed
```

## Project Structure
```
cinemaseat/
├── app/
│   ├── main.py          # FastAPI application
│   ├── config.py        # Configuration settings
│   └── models.py        # Database models (to be added)
├── tests/               # Test files (to be added)
├── docker/
│   └── Dockerfile       # Application container
├── docker-compose.yml   # Multi-container setup
└── requirements.txt     # Python dependencies
```

## Required Environment Variables
- `DATABASE_URL`: PostgreSQL connection string
- `GATEWAY_URL`: Mock payment gateway URL
- `HOLD_TTL_SECONDS`: Seat hold timeout in seconds (default: 300)

## Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (requires PostgreSQL running)
uvicorn app.main:app --reload
```

## API Endpoints

### Required Endpoints (for judging)
- `GET /health` - Health check (returns 200 in under 1 second)
- `GET /seats/{showtime_id}` - Get seat map for a showtime
- `POST /seats/{showtime_id}/hold` - Hold a specific seat

### Exact Request Formats (for judging)

#### Hold a Seat
```bash
POST /seats/{showtime_id}/hold
Content-Type: application/json

{
  "seat_id": 123,
  "user_identifier": "user_session_id_or_user_id"
}
```

Response (201 Created):
```json
{
  "hold_id": 456,
  "seat_id": 123,
  "row_letter": "F",
  "seat_number": 12,
  "hold_expires_at": "2026-08-08T10:05:00Z",
  "status": "held"
}
```

#### Get Seat Map
```bash
GET /seats/{showtime_id}
```

Response (200 OK):
```json
{
  "showtime_id": 1,
  "movie_title": "Spider-Man: Brand New Day",
  "start_time": "2026-08-09T20:00:00Z",
  "seats": [
    {
      "id": 1,
      "showtime_id": 1,
      "row_letter": "A",
      "seat_number": 1,
      "status": "available",
      "price": 15.00
    }
  ]
}
```

### Additional Endpoints
- `GET /movies` - List all movies
- `GET /movies/{movie_id}/showtimes` - Get showtimes for a movie
- `POST /bookings/{hold_id}/pay` - Initiate payment for a held seat
- `POST /bookings/callback` - Payment gateway callback endpoint
- `GET /bookings/{booking_id}` - Get booking details
- `GET /frontend` - Access the web frontend

## Concurrency Strategy
- PostgreSQL row locks for seat holding
- Advisory locks for distributed coordination
- Idempotent callback handling to prevent duplicate bookings