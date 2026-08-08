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

The app seeds sample movies, showtimes and seats automatically during container startup.

## Project Structure
```
cinemaseat/
|-- app/
|   |-- main.py          # FastAPI application
|   |-- config.py        # Configuration settings
|   `-- models.py        # Database models
|-- tests/               # Test files
|-- docker/
|   `-- Dockerfile       # Application container
|-- docker-compose.yml   # Multi-container setup
`-- requirements.txt     # Python dependencies
```

## Required Environment Variables
- `DATABASE_URL`: PostgreSQL connection string
- `GATEWAY_URL`: Mock payment gateway URL (for local Docker deployment)
- `HOLD_TTL_SECONDS`: Seat hold timeout in seconds (default: 300)
- `MOCK_PAYMENT`: Set to `true` to use mock payment without real gateway (for cloud deployment)
- `GATEWAY_TEST_MODE`: Set to `deterministic` for reliable testing with gateway
- `TEST_RETRY_LOGIC`: Set to `true` to test gateway retry logic (returns 500 from callback)

### Render Deployment Environment Variables
For Render deployment, add these environment variables:
```
DATABASE_URL=postgresql://user:password@host:port/database
GATEWAY_URL=https://your-gateway-service.onrender.com  # Optional: only if deploying gateway separately
HOLD_TTL_SECONDS=300
MOCK_PAYMENT=true  # Use mock payment on Render (recommended for hackathon)
TEST_RETRY_LOGIC=false  # Keep false in production
```

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

## Payment Gateway Integration

**Gateway**: asifmahmoud414/mock-gateway:latest

**Gateway behavior implemented**: real `/charge` integration, background payment initiation, idempotent callbacks, and race-mode callback lookup by `booking_ref`.

### Required Behaviors

1. **Async Payment Handler**: `/pay` returns `202` after creating a pending booking; gateway charging runs in the background.
2. **200 for Duplicate Callbacks**: Callback handler acknowledges duplicate/unknown events to avoid retry storms.
3. **Idempotent Callbacks**: Uses `event_id` and booking status checks for deduplication.
4. **Race Callback Support**: Falls back to gateway `booking_ref` if the callback arrives before `payment_id` is saved.
5. **Gateway Failure Handling**: Failed/timeout charge attempts mark the booking failed and release the held seat.
6. **No Double-Booking Goal**: Seat holds use PostgreSQL row locking and payment callbacks only confirm an existing pending booking.

### Control Headers Support

Environment variable `GATEWAY_TEST_MODE=deterministic` adds `X-Mock-Mode: deterministic` header for reliable testing.

### Gateway Misbehavior Handling

- **10% Failure Rate**: Booking marked as failed, seat released.
- **8% Duplicate Rate**: Handled via event ID and booking status checks.
- **2% Timeout Rate**: Background charge task marks pending booking failed if no callback succeeded.
- **2-15 Second Delays**: `/pay` does not wait for final callback completion.
- **Race callback**: Callback can confirm by `booking_ref` before `/charge` returns.

### Payment Response

`POST /bookings/{hold_id}/pay` returns immediately with a pending booking. `payment_id` may be `null` until the gateway `/charge` response or callback is processed.

```json
{
  "booking_id": 1,
  "payment_id": null,
  "status": "pending",
  "message": "Payment accepted. Gateway charge is running in the background."
}
```

## Concurrency Strategy
- PostgreSQL row locks for seat holding
- Idempotent callback handling to prevent duplicate bookings
- Expired holds are released from request paths as well as the periodic cleanup thread

## Required Proof Still To Run Before Submission

- Scenario A: fire 100 concurrent hold requests for one exact seat; report 1 success, 99 clean rejections, oversell 0.
- Scenario B: run with short `HOLD_TTL_SECONDS`, hold a seat, wait for expiry, show it becomes available and can be booked by another user.
- Gateway forced modes: test duplicate, fail, timeout and race headers against the real gateway container.
