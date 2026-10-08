# API Plan

## Public/customer
- POST `/api/v1/auth/register/`
- POST `/api/v1/auth/login/`
- POST `/api/v1/auth/refresh/`
- GET/PATCH `/api/v1/auth/me/`
- GET/POST `/api/v1/auth/addresses/`
- GET `/api/v1/stores/`
- GET `/api/v1/stores/?lat=...&lng=...`
- GET `/api/v1/catalog/categories/`
- GET `/api/v1/catalog/products/`
- GET `/api/v1/inventory/?store=<uuid>`
- GET `/api/v1/cart/`
- GET `/api/v1/orders/`
- GET `/api/v1/orders/<uuid>/`
- POST `/api/v1/payments/webhooks/flutterwave/`

## Next implementation layer
Add cart mutation, atomic checkout, Flutterwave initialize/verify, staff fulfillment actions,
rider assignment/status, device-token registration, notification feeds, promo validation,
loyalty ledger endpoints, reviews, support tickets, audit logs and role-scoped dashboards.
