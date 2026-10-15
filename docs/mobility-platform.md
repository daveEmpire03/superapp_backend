# Bokku Mart Mobility Platform

This release adds passenger rides and independent parcel shipments without changing the existing grocery `Order` / `Delivery` lifecycle.

## Domains

- **Grocery delivery:** remains in `apps.delivery` and is tied one-to-one to a grocery order.
- **Passenger rides:** `apps.rides` manages passenger trips, driver profiles, dispatch, fare estimates, and trip status history.
- **Independent parcels:** `apps.parcels` manages sender/recipient details, package sizing, courier assignment, proof-of-delivery code, and parcel history.
- **Payments:** existing order payment flows remain in place. `ServicePayment` handles Flutterwave checkout for rides and parcels separately from grocery orders.

## Passenger ride API

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/rides/quote/` | Estimate fare without creating a ride |
| POST | `/api/v1/rides/` | Request a ride |
| GET | `/api/v1/rides/` | List passenger's rides |
| GET | `/api/v1/rides/{uuid}/` | Read passenger's own ride |
| POST | `/api/v1/rides/{uuid}/cancel/` | Cancel an eligible unpaid ride |

## Driver API

| Method | Endpoint | Purpose |
|---|---|---|
| GET/POST/PATCH | `/api/v1/rides/driver/profile/` | Read/create/update vehicle profile |
| POST | `/api/v1/rides/driver/location/` | Record a fresh driver location |
| POST | `/api/v1/rides/driver/availability/` | Go online/offline |
| GET | `/api/v1/rides/driver/available/` | Find nearby matching rides |
| GET | `/api/v1/rides/driver/mine/` | List current assigned rides |
| POST | `/api/v1/rides/{uuid}/accept/` | Atomically accept a ride |
| POST | `/api/v1/rides/{uuid}/status/` | Advance assigned → arriving → in progress → completed |

A driver must have an active `RIDER` account, a vehicle profile approved by an operations administrator, a fresh location, and availability. A driver cannot accept a second active ride/parcel.

## Independent parcel API

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/parcels/quote/` | Estimate parcel fare |
| POST | `/api/v1/parcels/` | Create parcel shipment; returns one-time delivery code to sender |
| GET | `/api/v1/parcels/` | List sender's shipments |
| GET | `/api/v1/parcels/{uuid}/` | Read sender's shipment |
| POST | `/api/v1/parcels/{uuid}/cancel/` | Cancel before pickup, if eligible |
| GET | `/api/v1/parcels/driver/available/` | Find nearby parcels |
| GET | `/api/v1/parcels/driver/mine/` | List current assigned parcels |
| POST | `/api/v1/parcels/{uuid}/accept/` | Accept a parcel |
| PATCH | `/api/v1/parcels/{uuid}/status/` | Pickup → in transit → delivered; delivery code required |

Large parcels require a car. Delivery confirmation codes are stored as password hashes and are invalidated after successful delivery. Share the code only with the intended recipient.

## Mobility payments

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/payments/services/initialize/` | Initialize Flutterwave payment for a ride or parcel |
| POST | `/api/v1/payments/services/verify/` | Server-side verification for the authenticated service owner |
| POST | `/api/v1/payments/webhooks/flutterwave/` | Existing signed webhook; also recognizes service payment references |

Never trust a Flutterwave redirect alone. Payment status changes only after the backend verifies transaction reference, provider status, currency, and amount. Grocery payments still use the original order-specific payment service.

## Configuration

Add these to the deployment environment and tune against actual Ibadan operating costs:

- `RIDE_ROUTE_DISTANCE_MULTIPLIER`
- `RIDE_CAR_BASE_FARE_NGN`
- `RIDE_CAR_PER_KM_FARE_NGN`
- `RIDE_MOTORCYCLE_BASE_FARE_NGN`
- `RIDE_MOTORCYCLE_PER_KM_FARE_NGN`
- `PARCEL_BASE_FARE_NGN`
- `PARCEL_PER_KM_FARE_NGN`
- `DRIVER_SEARCH_RADIUS_KM`
- `DRIVER_LOCATION_MAX_AGE_SECONDS`
- `MOBILITY_REQUEST_TIMEOUT_MINUTES`

These quotes currently use straight-line distance multiplied by a configurable factor. They are **estimates**, not road-route distances or guaranteed production fares. Integrate a routing provider before publishing exact distances, ETAs, or final fares.

## Operations checklist

1. Create/verify driver accounts with role `RIDER`.
2. Driver submits vehicle profile.
3. An admin approves or suspends the profile in Django Admin → Ride driver profiles.
4. Configure Flutterwave credentials and a real `PAYMENT_REDIRECT_URL` for the customer Flutter app.
5. Configure Firebase credentials/device tokens for push delivery.
6. Run migrations and the complete backend test suite before deployment.
7. Test cancellation/refund policy, poor connectivity, stale GPS, simultaneous driver acceptance, and provider webhook retries.
8. Deploy the driver app only after Android/iOS location permission descriptions, signing, privacy policy, and physical-device tests are complete.

## Current boundaries

- Driver discovery is pull-based plus push notifications to nearby online drivers; it is not a central auto-dispatch algorithm.
- Driver location updates are currently foreground/API updates, not guaranteed background tracking.
- Cancellation of already-paid mobility jobs is blocked until a refund workflow is implemented; do not manually mark such jobs cancelled.
- Identity/document verification, fraud review, support disputes, live map routing, and production ETA calculations need operational integration before public launch.
