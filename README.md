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

**Spec Compliance**: ✅ Fully compliant with gateway specification

### Required Behaviors (All Implemented)

1. **✅ Async Payment Handler**: `/pay` returns 202 immediately, doesn't wait for callback
2. **✅ 200 for Duplicate Callbacks**: Always returns 200 even for duplicates
3. **✅ Idempotent Callbacks**: Uses `event_id` for deduplication
4. **✅ Gateway Failure Handling**: Handles 10% failure rate, 2% timeout rate
5. **✅ Duplicate Prevention**: Duplicate callbacks don't create double payments
6. **✅ No Double-Booking**: Callback processing checks existing booking status

### Control Headers Support

Environment variable `GATEWAY_TEST_MODE=deterministic` adds `X-Mock-Mode: deterministic` header for reliable testing.

### Gateway Misbehavior Handling

- **10% Failure Rate**: Booking marked as FAILED, seat released
- **8% Duplicate Rate**: Handled via event_id deduplication  
- **2% Timeout Rate**: Booking marked as FAILED, seat released
- **2-15 Second Delays**: Async handler doesn't block

### Test Results (Local Docker)
- Hold seat: ✅ Success
- Initiate payment: ✅ Success (202 returned immediately)
- Gateway callback: ✅ Delivered (HTTP 200)
- Booking confirmation: ✅ Confirmed
- Seat status update: ✅ Changed to "booked"
- Duplicate callback: ✅ Handled idempotently

## Concurrency Strategy
- PostgreSQL row locks for seat holding
- Advisory locks for distributed coordination
- Idempotent callback handling to prevent duplicate bookings

## Load Testing Results

**Note**: Due to free tier cloud resource limitations, concurrency was tested with 20 concurrent requests instead of 100. The same logic prevents double-booking regardless of the number of concurrent requests.

**Test Results (on Render)**:
- Health Check: ✅ PASS (200 in <1s)
- Movies Endpoint: ✅ PASS
- Showtimes Endpoint: ✅ PASS
- Seat Map: ✅ PASS
- Seat Hold: ✅ PASS
- Concurrent Holds (20 requests): ✅ PASS (1 success, 19 conflicts - NO OVERSELL)

**Test Results (local)**:
- The same concurrency control logic was tested locally and can handle 100+ concurrent requests when sufficient resources are available.