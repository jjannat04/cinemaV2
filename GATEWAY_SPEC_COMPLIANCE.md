# Gateway Specification Compliance

## Overview
This document explains how the CinemaSeat system complies with the mock gateway specification.

## Required Behaviors (All Implemented ✅)

### 1. Async Payment Handler
**Requirement**: "/pay handler cannot wait for the gateway. It must return quickly and let the callback finish the job."

**Implementation**: 
- `/pay` endpoint returns HTTP 202 immediately after initiating gateway call
- Booking status set to PENDING
- Callback endpoint completes the actual payment processing
- No blocking wait for gateway response

**Code**: `app/routers/bookings.py` lines 90-166

### 2. 200 for Duplicate Callbacks
**Requirement**: "Always return 200 from your callback handler, even for a duplicate. A non-200 tells the gateway that delivery failed, and it will retry forever."

**Implementation**:
- Callback handler ALWAYS returns HTTP 200
- Duplicate detection happens BEFORE returning
- Even processing errors return 200 to prevent infinite retries
- Status message indicates what happened

**Code**: `app/routers/bookings.py` lines 168-276

### 3. Idempotent Callbacks
**Requirement**: "A duplicate callback must not create a second payment, must not confirm the booking twice, and must not double-count revenue."

**Implementation**:
- Uses `event_id` for deduplication
- Checks if booking already processed
- Checks if booking already in final state (CONFIRMED/FAILED)
- Only processes if not already completed
- Store event_id for future duplicate detection

**Code**: `app/routers/bookings.py` lines 197-208

### 4. Gateway Failure Handling
**Requirement**: Handle gateway misbehavior (10% failure rate, 2% timeout rate, 8% duplicate rate)

**Implementation**:
- **10% Failure Rate**: Booking marked as FAILED, seat released
- **2% Timeout Rate**: Booking marked as FAILED, seat released  
- **8% Duplicate Rate**: Handled via event_id deduplication
- **Connection Errors**: Booking marked as FAILED, seat released
- **Unknown Payment IDs**: Return 200, log warning

**Code**: `app/routers/bookings.py` lines 143-166, 187-190, 218-235

### 5. Callback Delays (2-15 seconds)
**Requirement**: Handle random callback delays (2-15 seconds)

**Implementation**:
- Async handler doesn't block
- Booking remains in PENDING state during delay
- Frontend polls booking status for updates
- Hold remains active during payment processing

**Code**: `app/routers/bookings.py` lines 133-136

## Control Headers Support

### Available Headers
- `X-Mock-Mode: deterministic` - 2 second delay, always succeeds, no duplicates
- `X-Mock-Force: fail` - Guaranteed failure
- `X-Mock-Force: duplicate` - Guaranteed duplicate callback
- `X-Mock-Force: timeout` - Guaranteed timeout on /charge
- `X-Mock-Force: race` - Callback arrives before /charge returns
- `X-Mock-Force: success` - Guaranteed clean success

### Implementation
Environment variable `GATEWAY_TEST_MODE=deterministic` automatically adds `X-Mock-Mode: deterministic` header for reliable testing during development.

**Code**: `app/routers/bookings.py` lines 131-134

## Testing

### Deterministic Mode
```bash
# Set environment variable for deterministic testing
GATEWAY_TEST_MODE=deterministic
```

This ensures:
- Consistent 2-second delays
- No random failures
- No duplicate callbacks
- Reliable for development and testing

### Production Mode
```bash
# No GATEWAY_TEST_MODE set
# Gateway uses random behavior (10% failures, 8% duplicates, etc.)
```

## Gateway Misbehavior Scenarios

### Scenario 1: Payment Fails (10% rate)
1. User initiates payment
2. Gateway returns FAILED status
3. Callback marks booking as FAILED
4. Seat released back to AVAILABLE
5. User can try again

### Scenario 2: Duplicate Callback (8% rate)
1. User initiates payment
2. Gateway delivers SUCCESS callback
3. Booking confirmed, seat booked
4. Gateway delivers duplicate callback
5. System detects duplicate via event_id
6. Returns 200, no changes made

### Scenario 3: Gateway Timeout (2% rate)
1. User initiates payment
2. Gateway times out (HTTP 500 or timeout)
3. Booking marked as FAILED
4. Seat released back to AVAILABLE
5. User can try again

### Scenario 4: Race Condition (X-Mock-Force: race)
1. User initiates payment
2. Callback arrives before /charge returns
3. System handles this correctly:
   - If callback arrives first: Booking already in PENDING state
   - If /charge returns first: Returns 202, callback processes normally
4. No double-booking or inconsistent states

## Summary

**✅ Fully Compliant**: All required behaviors from the gateway specification are implemented

**✅ Production Ready**: Handles all gateway misbehaviors gracefully

**✅ Testable**: Supports control headers for deterministic testing

**✅ Idempotent**: Duplicate callbacks handled correctly

**✅ No Double-Booking**: Concurrency control + idempotent callbacks ensure safety