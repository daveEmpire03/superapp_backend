"""Permission callbacks used by the Unfold sidebar navigation."""


def _has_permission(request, permission):
    return request.user.is_authenticated and request.user.has_perm(permission)


def can_view_orders(request):
    return _has_permission(request, "orders.view_order")


def can_view_payments(request):
    return _has_permission(request, "payments.view_payment")


def can_view_carts(request):
    return _has_permission(request, "cart.view_cart")


def can_view_promotions(request):
    return _has_permission(request, "promotions.view_promotion")


def can_view_products(request):
    return _has_permission(request, "catalog.view_product")


def can_view_categories(request):
    return _has_permission(request, "catalog.view_category")


def can_view_inventory(request):
    return _has_permission(request, "inventory.view_storeinventory")


def can_view_inventory_movements(request):
    return _has_permission(request, "inventory.view_inventorymovement")


def can_view_users(request):
    return _has_permission(request, "accounts.view_user")


def can_view_addresses(request):
    return _has_permission(request, "accounts.view_address")


def can_view_stores(request):
    return _has_permission(request, "stores.view_store")


def can_view_store_memberships(request):
    return _has_permission(request, "stores.view_storestaffmembership")


def can_view_deliveries(request):
    return _has_permission(request, "delivery.view_delivery")


def can_view_support(request):
    return _has_permission(request, "support.view_supportticket")


def can_view_reviews(request):
    return _has_permission(request, "reviews.view_review")


def can_view_loyalty(request):
    return _has_permission(request, "loyalty.view_loyaltyentry")


def can_view_analytics(request):
    return _has_permission(request, "analytics.view_analyticsevent")


def can_view_notifications(request):
    return _has_permission(request, "notifications.view_notification")
