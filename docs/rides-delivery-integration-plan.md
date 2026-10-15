# Bokku Mart Rides and Delivery Integration Plan

## Status

Planning document only. No production behavior, database schema, payment flow, or existing grocery workflow is changed by this plan.

## Goals

Extend the existing Bokku Mart platform with:
- Passenger ride booking and trip tracking.
- Independent parcel delivery.
- Continued support for existing grocery orders and store fulfillment.
- A shared driver/courier operational experience where the domain rules allow it.
- Administrative controls for driver approval, fares, service availability, cancellations, disputes, and trip/order monitoring.

The initial rollout should be limited to one launch city, with city-specific service zones and pricing configurable rather than hard-coded. Ibadan is a proposed starting point, subject to confirmation.

## Repository findings

### Flutter customer app — `daveEmpire03/superapp`

- Uses Flutter, Riverpod 3, GoRouter, Dio, GetIt, and Geolocator.
- Feature code is organized under `lib/features`.
- The router is centralized in `lib/core/router/app_router.dart`.
- The home screen already owns the grocery discovery experience; service entry points should be added without replacing catalog, store selection, cart, or checkout behavior.
- The app currently has a customer-facing experience. A dedicated driver application is a product decision, not an existing capability confirmed by this inspection.

### Django backend — `daveEmpire03/superapp_backend`

- Uses Django REST Framework, PostgreSQL, Redis/Celery, JWT authentication, and a versioned API.
- Existing domain apps include accounts, stores, catalog, inventory, cart, orders, payments, and delivery.
- The README documents rider delivery endpoints and existing delivery flows. Inspect `apps/delivery/models.py`, serializers, services, URLs, views, permissions, migrations, and tests before deciding what to reuse.
- Grocery order totals and inventory decisions must remain server-authoritative.
- Payment state must remain separate from fulfillment state; webhook payloads must not be treated as final proof of payment without provider verification.

## Domain boundaries

### Grocery orders (existing)

Keep the current cart, checkout, stock reservation, store inventory, payment verification, and grocery order state transitions intact. Grocery delivery remains linked to its originating grocery order.

### Parcel delivery (extend existing delivery domain)

Represent an independent sender-to-recipient parcel job with validated pickup/drop-off coordinates and addresses, package details, contact details, quoted fee, payment state, courier assignment, status history, cancellation rules, and delivery proof. Reuse existing delivery models/endpoints only after verifying their semantics and backward compatibility.

### Passenger rides (new domain)

Create a dedicated ride domain for:
- Ride requests and immutable pickup/drop-off snapshots.
- Vehicle/service type and fare quotes with an explicit quote expiry.
- Driver onboarding, approval, service eligibility, and availability.
- Dispatch attempts, acceptance timeout, reassignment, and idempotent accept/cancel actions.
- Trip state history and server-validated transitions.
- Location pings with freshness limits and access controls.
- Separate trip/payment state, receipts, cancellation fees, and platform commission ledger entries.

Do not overload grocery order status fields to represent rides.

## Proposed passenger trip lifecycle

`requested -> searching -> driver_assigned -> driver_arriving -> driver_arrived -> in_progress -> completed`

Terminal alternatives: `cancelled`, `no_driver_found`, and `expired`.

Transitions must be enforced server-side. A driver must not accept overlapping active jobs, and concurrent accept attempts must be resolved atomically. Every mutation that can be retried should have a defined idempotency strategy.

## API outline (to refine after inspecting current URL conventions)

- `GET /api/v1/rides/service-types/`
- `POST /api/v1/rides/quotes/`
- `POST /api/v1/rides/`
- `GET /api/v1/rides/{id}/`
- `POST /api/v1/rides/{id}/cancel/`
- `POST /api/v1/driver/availability/`
- `POST /api/v1/driver/location/`
- `POST /api/v1/driver/rides/{id}/accept/`
- `POST /api/v1/driver/rides/{id}/arrived/`
- `POST /api/v1/driver/rides/{id}/start/`
- `POST /api/v1/driver/rides/{id}/complete/`

These paths are proposals, not claims that the endpoints currently exist. Reuse the backend's established API naming and permission conventions when implementation begins.

## Flutter feature structure

Add feature modules following the existing `lib/features` conventions, with presentation, domain, and data layers:

- `features/rides/domain`: entities, repository contracts, use cases.
- `features/rides/data`: API data source, DTO/models, repository implementation.
- `features/rides/presentation`: Riverpod providers/controllers and screens.
- `features/parcel_delivery/` or the existing delivery feature: use the existing structure after inspection; avoid duplicate concepts.
- Add routes to the existing GoRouter; do not introduce a competing router.
- Register dependencies through the current dependency-injection setup.
- Preserve the existing app theme, auth behavior, and grocery navigation.

## Suggested screen scope

Customer:
- Home service selector: Shop, Ride, Send a parcel.
- Pickup and destination selection.
- Map preview, location search, and manual address fallback.
- Vehicle/service selection and server-issued fare quote.
- Searching/assigned-driver screen, trip tracking, cancellation, trip history, and receipt.
- Parcel details, recipient details, delivery quote, tracking, and proof of delivery.

Driver:
- Onboarding and document review.
- Availability toggle and incoming job offer.
- Accept/decline, navigation handoff, arrival, start, completion, and earnings history.
- A dedicated driver app is recommended for operational clarity and permissions, but can be deferred if the initial MVP requires one binary.

Admin/operations:
- Driver approval and suspension.
- Service zones and fare configuration.
- Active rides/deliveries, assignment history, cancellation and dispute handling.
- Payment/commission reconciliation and audit history.

## Safety, security, and reliability requirements

- Require authenticated, role-authorized endpoints for customers, drivers, and operations.
- Validate coordinates, service zones, vehicle eligibility, and quote expiry server-side.
- Do not expose exact driver location to unrelated users; restrict access to the active customer/driver and authorized operations.
- Rate-limit location updates and validate timestamps and coordinate bounds.
- Enforce atomic job assignment and one-active-job constraints at the database/service boundary.
- Use server-generated prices; clients must not submit trusted fare totals.
- Keep payment and trip/delivery statuses separate.
- Store audit/history records for assignment and status transitions.
- Design reconnect behavior for WebSocket updates and provide authenticated polling fallback.
- Avoid collecting continuous location when the driver is offline or no active job requires it.
- Add tests for permission boundaries, invalid transitions, race conditions, cancellation, quote expiry, and payment verification.

## Implementation sequence

1. **Read-only audit:** inspect current delivery models/services/views/serializers/URLs/tests, authentication/role handling, payment services, ASGI/channel support, Flutter router/home shell, dependency registration, API client conventions, and current test status.
2. **Contract and decisions:** settle launch city, vehicle types, cash/online payment support, driver app strategy, pricing model, service zones, and map provider; document API contracts and state machines.
3. **Backend ride foundation:** add the ride domain, models/migrations, serializers, services, permission rules, endpoints, admin configuration, and focused tests. Do not merge until migrations and regression tests pass.
4. **Customer ride UI:** add Riverpod feature modules and GoRouter routes, connecting to real endpoints; handle loading, empty, offline, denied-location, and server errors.
5. **Dispatch and live updates:** add atomic assignment, expiry/reassignment, location updates, WebSocket events or authenticated polling fallback, and concurrency tests.
6. **Parcel delivery integration:** extend existing delivery functionality for independent parcels without changing grocery-order delivery behavior; test both paths.
7. **Driver experience:** implement the selected driver app/mode, onboarding, availability, job handling, and trip lifecycle.
8. **Payments and operations:** provider verification, cash collection records, commission ledger, reconciliation, admin workflows, and audit trails.
9. **End-to-end verification:** run Django checks/migrations/tests, Flutter format/analyze/tests, API contract tests, and manual customer/driver/admin flows in staging.
10. **Controlled launch:** enable the feature by city/service flags, monitor errors and assignment metrics, and expand only after operational validation.

## Acceptance criteria

- Existing grocery browse/cart/checkout/order and delivery flows pass their current tests and remain behaviorally unchanged.
- Customers cannot spoof fares or access another customer's trip.
- Drivers cannot accept jobs they are not approved/eligible for or accept conflicting active jobs.
- Assignment is safe under concurrent requests and retries.
- Trip/delivery status transitions are validated and auditable.
- Location permission is optional for grocery browsing; ride booking supports manual pickup/drop-off entry if location permission is denied.
- Fare, payment, cancellation, and commission records reconcile on the backend.
- No production API keys or credentials are committed.

## Open decisions before implementation

1. Launch city: proposed Ibadan.
2. Passenger vehicles: cars only, motorcycles only, or both.
3. Parcel delivery: motorbike couriers, cars, or both.
4. Payment: cash, online, or both.
5. Driver experience: separate Flutter driver app (recommended) or driver mode inside the customer app.
6. Map provider and pricing basis (distance, time, base fare, minimum fare, and zone/traffic rules).
