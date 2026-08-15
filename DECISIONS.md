

This document documents three key architectural decisions made during the development of CinemaSeat.

## Decision 1: Monolithic Architecture vs. Microservices

### Options Considered

1. **Monolithic Architecture**: Single FastAPI application with one PostgreSQL database
2. **Microservices**: Separate services for movies, bookings, payments, and seats

### What I Chose

**Monolithic Architecture** - A single FastAPI application with PostgreSQL database.

### Why I Chose This

- **Simplicity**: For an 8-hour hackathon, monolithic architecture reduces operational complexity
- **Performance**: No inter-service network latency, which is critical for high-concurrency seat booking
- **Transaction Management**: Single database connection allows proper ACID transactions across booking operations
- **Debugging**: Easier to trace issues and debug in a single codebase
- **Deployment**: Docker Compose can spin up the entire stack with a single command

### What I Gave Up

- **Independent Scaling**: Cannot scale individual components separately
- **Technology Flexibility**: All components must use the same tech stack
- **Fault Isolation**: A bug in one component can potentially affect the entire system

---

## Decision 2: PostgreSQL-Only vs. PostgreSQL + Redis for Seat Locking

### Options Considered

1. **PostgreSQL + Redis**: Use Redis for fast seat locking with TTL, PostgreSQL for persistent data
2. **PostgreSQL Only**: Use PostgreSQL row locks and advisory locks for all concurrency control

### What I Chose

**PostgreSQL Only** - Using row locks (`SELECT FOR UPDATE`) and advisory locks for seat management.

### Why I Chose This

- **Simplicity**: Single database reduces infrastructure complexity and potential points of failure
- **ACID Guarantees**: PostgreSQL provides strong consistency guarantees for booking operations
- **Row Locks**: `SELECT FOR UPDATE` provides database-level locking that prevents race conditions
- **No Additional Infrastructure**: No need to manage Redis cluster, connection pooling, or cache invalidation
- **Sufficient Performance**: For the expected load, PostgreSQL row locks provide adequate performance

### What I Gave Up

- **Raw Performance**: Redis would provide slightly faster lock acquisition
- **TTL Handling**: Redis has built-in TTL expiration; I had to implement a background cleanup task
- **Distributed Locking**: Redis would be better if I ever needed truly distributed locking across multiple database instances

---

## Decision 3: Synchronous vs. Asynchronous Payment Gateway Integration

### Options Considered

1. **Synchronous**: Wait for payment gateway response before returning to user
2. **Asynchronous**: Return immediately, let callback handle confirmation

### What I Chose

**Asynchronous Integration** - Return 202 Accepted immediately, process payment via callback.

### Why I Chose This

- **Gateway Behavior**: The mock gateway has documented delays (2-15 seconds) and potential timeouts
- **User Experience**: Users get immediate feedback rather than waiting 15+ seconds
- **Resilience**: If gateway is slow or times out, our application remains responsive
- **Scalability**: Async handling allows our application to handle more concurrent requests
- **Problem Statement Requirement**: The problem explicitly states "Your /pay handler cannot wait for the gateway"

### What I Gave Up

- **Complexity**: More complex state management (pending, confirmed, failed states)
- **Idempotency Requirements**: Must handle duplicate callbacks carefully
- **User Feedback**: Users don't get immediate confirmation of payment success
- **Error Handling**: More edge cases to handle (callbacks that never arrive, delayed callbacks, etc.)

---

## Summary

These decisions reflect a pragmatic approach suitable for an 8-hour hackathon:

- Prioritized simplicity and operational reliability over theoretical performance
- Chose battle-tested technologies (PostgreSQL row locks) over complex distributed systems
- FolloId the problem statement's explicit requirements for async payment handling
- Maintained focus on the core challenge: preventing double-booking under high concurrency

The resulting system is:

- **Correct**: Uses database locks to prevent double-booking
- **Deployable**: Docker Compose brings up the entire stack
- **Testable**: Includes unit tests for concurrency and idempotency
- **Observable**: Includes health checks and proper error handling
