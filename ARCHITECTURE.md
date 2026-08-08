# CinemaSeat System Architecture

## Overview
A monolithic FastAPI application with PostgreSQL database, designed to handle high-concurrency seat booking without double-booking.

## Architecture Diagram
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   FastAPI App   │────▶│  PostgreSQL     │
│  (HTML/JS)      │     │   (Python)      │     │   Database      │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                │
                                │
                                ▼
                       ┌─────────────────┐
                       │  Mock Gateway  │
                       │  (Payment/OTP) │
                       └─────────────────┘
```

## Design Decisions

### 1. Monolithic Architecture
**Choice**: Single FastAPI application instead of microservices

**Rationale**:
- Simpler deployment and debugging for an 8-hour hackathon
- Lower latency (no inter-service network calls)
- Easier transaction management (single database connection)
- PostgreSQL row locks provide sufficient concurrency control

**Trade-offs**:
- Less flexible scaling
- Single point of failure (mitigated by containerization)

### 2. PostgreSQL-Only Approach
**Choice**: Using PostgreSQL row locks instead of Redis for seat locking

**Rationale**:
- Single database simplifies operations
- ACID transactions ensure data consistency
- Row locks prevent double-booking at database level
- Advisory locks for distributed coordination
- No additional infrastructure complexity

**Trade-offs**:
- Slightly lower performance than Redis
- Database becomes bottleneck under extreme load

### 3. Concurrency Strategy
**Implementation**:
- **SELECT FOR UPDATE**: Row-level locking when holding seats
- **Advisory Locks**: Cross-process coordination for critical sections
- **Idempotent Callbacks**: Handle duplicate payment callbacks safely
- **TTL-based Expiration**: PostgreSQL scheduled jobs or application-level cleanup

### 4. Payment Gateway Integration
**Strategy**:
- Asynchronous callback handling (don't wait for gateway)
- Idempotent callback processing (handle duplicates)
- Optimistic locking for payment status updates
- Callback URL as environment variable

## Data Model

### Core Entities
- **Movie**: Movie details
- **Theatre**: Physical theatre layout
- **Showtime**: Specific movie screening
- **Seat**: Individual seat with status
- **SeatHold**: Temporary seat reservation with TTL
- **Booking**: Finalized booking with payment info

### Key Relationships
- Showtime → Movie (many-to-one)
- Showtime → Theatre (many-to-one)
- Showtime → Seats (one-to-many)
- Seat → SeatHold (one-to-many)
- SeatHold → Booking (one-to-one)

## API Design

### Core Endpoints
1. `GET /health` - Health check (required)
2. `GET /movies` - List available movies
3. `GET /showtimes/{movie_id}` - Get showtimes for a movie
4. `GET /seats/{showtime_id}` - Get seat map (required)
5. `POST /seats/{showtime_id}/hold` - Hold a seat (required)
6. `POST /bookings/{hold_id}/pay` - Initiate payment
7. `POST /callback` - Payment gateway callback

### Concurrency Handling
- Use `SELECT FOR UPDATE` when checking seat availability
- Implement retry logic for lock acquisition failures
- Return 409 Conflict when seat is unavailable
- Use database constraints to prevent duplicate bookings

## Error Handling
- **409 Conflict**: Seat already held/booked
- **400 Bad Request**: Invalid input
- **500 Internal Server Error**: Unexpected errors
- **503 Service Unavailable**: Gateway/Database issues

## Security Considerations
- Environment-based configuration
- Input validation via Pydantic
- SQL injection prevention via SQLAlchemy
- Callback signature verification (bonus task)

## Scalability Strategy
- Database connection pooling
- Horizontal scaling via containerization
- Load balancing (bonus task)
- Database read replicas (future enhancement)