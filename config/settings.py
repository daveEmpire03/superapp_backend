from datetime import timedelta
from pathlib import Path
import os

import dj_database_url
from celery.schedules import crontab
from dotenv import load_dotenv
from django.templatetags.static import static
from django.urls import reverse_lazy


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


# -----------------------------------------------------------------------------
# Core
# -----------------------------------------------------------------------------

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "unsafe-development-key",
)

DEBUG = (
    os.getenv(
        "DJANGO_DEBUG",
        "False",
    ).lower()
    == "true"
)

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "DJANGO_ALLOWED_HOSTS",
        "127.0.0.1,localhost",
    ).split(",")
    if host.strip()
]


# -----------------------------------------------------------------------------
# Applications
# -----------------------------------------------------------------------------

DJANGO_APPS = [
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "django_celery_results",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.stores",
    "apps.catalog",
    "apps.inventory",
    "apps.cart",
    "apps.orders",
    "apps.payments",
    "apps.delivery",
    "apps.promotions",
    "apps.loyalty",
    "apps.notifications",
    "apps.reviews",
    "apps.support",
    "apps.analytics",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


# -----------------------------------------------------------------------------
# Middleware
# -----------------------------------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# -----------------------------------------------------------------------------
# URLs / Templates
# -----------------------------------------------------------------------------

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": ("django.template.backends." "django.DjangoTemplates"),
        "DIRS": [
            BASE_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                ("django.template.context_processors." "request"),
                ("django.contrib.auth." "context_processors.auth"),
                ("django.contrib.messages." "context_processors.messages"),
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------

DATABASES = {
    "default": dj_database_url.config(
        default=(f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=600,
    )
}


# -----------------------------------------------------------------------------
# Authentication
# -----------------------------------------------------------------------------

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": ("django.contrib.auth.password_validation." "MinimumLengthValidator"),
    },
    {
        "NAME": ("django.contrib.auth.password_validation." "CommonPasswordValidator"),
    },
    {
        "NAME": ("django.contrib.auth.password_validation." "NumericPasswordValidator"),
    },
]


# -----------------------------------------------------------------------------
# Internationalization
# -----------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Africa/Lagos"

USE_I18N = True
USE_TZ = True


# -----------------------------------------------------------------------------
# Static / Media
# -----------------------------------------------------------------------------

STATIC_URL = "static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"

MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# -----------------------------------------------------------------------------
# Django REST Framework
# -----------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        ("rest_framework_simplejwt." "authentication.JWTAuthentication"),
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": (
        ("django_filters.rest_framework." "DjangoFilterBackend"),
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_SCHEMA_CLASS": ("drf_spectacular.openapi.AutoSchema"),
    "DEFAULT_PAGINATION_CLASS": ("core.pagination.StandardPagination"),
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": ("core.exceptions.api_exception_handler"),
}


# -----------------------------------------------------------------------------
# JWT
# -----------------------------------------------------------------------------

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=30,
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=30,
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}


# -----------------------------------------------------------------------------
# API Documentation
# -----------------------------------------------------------------------------

SPECTACULAR_SETTINGS = {
    "TITLE": "Bokku Mart API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}


# -----------------------------------------------------------------------------
# CORS
# -----------------------------------------------------------------------------

CORS_ALLOW_ALL_ORIGINS = (
    os.getenv(
        "CORS_ALLOW_ALL_ORIGINS",
        "True",
    ).lower()
    == "true"
)


# -----------------------------------------------------------------------------
# Email
# -----------------------------------------------------------------------------

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)

EMAIL_HOST = os.getenv(
    "EMAIL_HOST",
    "smtp.gmail.com",
)

EMAIL_PORT = int(
    os.getenv(
        "EMAIL_PORT",
        "587",
    )
)

EMAIL_USE_TLS = (
    os.getenv(
        "EMAIL_USE_TLS",
        "True",
    ).lower()
    == "true"
)

EMAIL_USE_SSL = (
    os.getenv(
        "EMAIL_USE_SSL",
        "False",
    ).lower()
    == "true"
)

EMAIL_HOST_USER = os.getenv(
    "EMAIL_HOST_USER",
    "",
)

EMAIL_HOST_PASSWORD = os.getenv(
    "EMAIL_HOST_PASSWORD",
    "",
)

DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    EMAIL_HOST_USER or "webmaster@localhost",
)

SERVER_EMAIL = DEFAULT_FROM_EMAIL

EMAIL_TIMEOUT = int(
    os.getenv(
        "EMAIL_TIMEOUT",
        "15",
    )
)


# -----------------------------------------------------------------------------
# Celery / Redis
# -----------------------------------------------------------------------------

CELERY_BROKER_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379/0",
)

CELERY_RESULT_BACKEND = "django-db"

CELERY_TASK_TRACK_STARTED = True

CELERY_BEAT_SCHEDULE = {
    "expire-order-reservations": {
        "task": ("apps.orders.tasks." "expire_due_order_reservations"),
        "schedule": crontab(
            minute="*",
        ),
    },
}


# -----------------------------------------------------------------------------
# Flutterwave
# -----------------------------------------------------------------------------

FLUTTERWAVE_SECRET_KEY = os.getenv(
    "FLUTTERWAVE_SECRET_KEY",
    "",
)

FLUTTERWAVE_SECRET_HASH = os.getenv(
    "FLUTTERWAVE_SECRET_HASH",
    "",
)


# -----------------------------------------------------------------------------
# Firebase
# -----------------------------------------------------------------------------

FIREBASE_CREDENTIALS_PATH = os.getenv(
    "FIREBASE_CREDENTIALS_PATH",
    "",
)


# -----------------------------------------------------------------------------
# Security
# -----------------------------------------------------------------------------

SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = "DENY"

# -----------------------------------------------------------------------------
# Django Unfold Admin
# -----------------------------------------------------------------------------

UNFOLD = {
    "SITE_TITLE": "Bokku Mart Admin",
    "SITE_HEADER": "Bokku Mart",
    "SITE_SUBHEADER": "Management Dashboard",
    "SITE_SYMBOL": "storefront",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "BORDER_RADIUS": "8px",
    "STYLES": [lambda request: static("admin/css/bokku-dashboard.css")],
    "DASHBOARD_CALLBACK": "core.admin_dashboard.dashboard_callback",
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {"title": "Overview", "separator": False, "items": [
                {"title": "Dashboard", "icon": "dashboard", "link": reverse_lazy("admin:index")},
            ]},
            {"title": "Commerce", "separator": True, "items": [
                {"title": "Orders", "icon": "shopping_bag", "link": reverse_lazy("admin:orders_order_changelist"), "permission": "orders.view_order"},
                {"title": "Payments", "icon": "payments", "link": reverse_lazy("admin:payments_payment_changelist"), "permission": "payments.view_payment"},
                {"title": "Carts", "icon": "shopping_cart", "link": reverse_lazy("admin:cart_cart_changelist"), "permission": "cart.view_cart"},
                {"title": "Promotions", "icon": "sell", "link": reverse_lazy("admin:promotions_promotion_changelist"), "permission": "promotions.view_promotion"},
            ]},
            {"title": "Catalogue & stock", "separator": True, "items": [
                {"title": "Products", "icon": "inventory_2", "link": reverse_lazy("admin:catalog_product_changelist"), "permission": "catalog.view_product"},
                {"title": "Categories", "icon": "category", "link": reverse_lazy("admin:catalog_category_changelist"), "permission": "catalog.view_category"},
                {"title": "Store inventory", "icon": "warehouse", "link": reverse_lazy("admin:inventory_storeinventory_changelist"), "permission": "inventory.view_storeinventory"},
                {"title": "Stock movements", "icon": "swap_vert", "link": reverse_lazy("admin:inventory_inventorymovement_changelist"), "permission": "inventory.view_inventorymovement"},
            ]},
            {"title": "People & fulfilment", "separator": True, "items": [
                {"title": "Customers & staff", "icon": "group", "link": reverse_lazy("admin:accounts_user_changelist"), "permission": "accounts.view_user"},
                {"title": "Addresses", "icon": "location_on", "link": reverse_lazy("admin:accounts_address_changelist"), "permission": "accounts.view_address"},
                {"title": "Stores", "icon": "store", "link": reverse_lazy("admin:stores_store_changelist"), "permission": "stores.view_store"},
                {"title": "Store memberships", "icon": "badge", "link": reverse_lazy("admin:stores_storestaffmembership_changelist"), "permission": "stores.view_storestaffmembership"},
                {"title": "Deliveries", "icon": "local_shipping", "link": reverse_lazy("admin:delivery_delivery_changelist"), "permission": "delivery.view_delivery"},
            ]},
            {"title": "Engagement & insights", "separator": True, "items": [
                {"title": "Support tickets", "icon": "support_agent", "link": reverse_lazy("admin:support_supportticket_changelist"), "permission": "support.view_supportticket"},
                {"title": "Reviews", "icon": "reviews", "link": reverse_lazy("admin:reviews_review_changelist"), "permission": "reviews.view_review"},
                {"title": "Loyalty", "icon": "loyalty", "link": reverse_lazy("admin:loyalty_loyaltyentry_changelist"), "permission": "loyalty.view_loyaltyentry"},
                {"title": "Analytics events", "icon": "query_stats", "link": reverse_lazy("admin:analytics_analyticsevent_changelist"), "permission": "analytics.view_analyticsevent"},
                {"title": "Notifications", "icon": "notifications", "link": reverse_lazy("admin:notifications_notification_changelist"), "permission": "notifications.view_notification"},
            ]},
        ],
    },
    "COLORS": {
        "primary": {
            "50": "#eff6ff",
            "100": "#dbeafe",
            "200": "#bfdbfe",
            "300": "#93c5fd",
            "400": "#60a5fa",
            "500": "#0000FF",
            "600": "#0000cc",
            "700": "#0000a3",
            "800": "#000080",
            "900": "#000066",
            "950": "#000033",
        },
    },
}
