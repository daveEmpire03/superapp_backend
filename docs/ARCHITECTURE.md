# Architecture

Flutter customer app, management/admin clients, store/staff client and rider client consume a versioned REST API.

## Core data ownership
- Product: global merchandising identity.
- StoreInventory: store-specific price, quantity and availability.
- Cart: customer + selected store.
- Order: immutable commercial snapshot.
- Payment: payment-provider lifecycle, separate from order lifecycle.
- Delivery: rider assignment and delivery lifecycle.
- LoyaltyEntry: ledger rather than a mutable points-only field.

## Reliability/security boundaries
- Never trust prices/totals sent by clients.
- Lock/re-check inventory during checkout.
- Use database transactions for checkout, stock reservation and payment finalization.
- Verify payment amount, currency, reference and provider transaction before marking PAID.
- Make payment webhooks idempotent.
- Restrict staff/store/rider endpoints by role and store assignment.
- Add throttling, audit logs, structured logs, monitoring and backups before production.
- Keep secrets in environment variables/secret manager.
