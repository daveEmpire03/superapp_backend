from django.contrib import admin
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import Group

from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import Address, User


@admin.register(User)
class CustomUserAdmin(UserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    ordering = ("email",)

    list_display = (
        "customer_id",
        "email",
        "phone",
        "role",
        "is_email_verified",
        "is_phone_verified",
        "is_staff",
        "is_active",
    )

    list_filter = (
        "role",
        "is_email_verified",
        "is_phone_verified",
        "is_staff",
        "is_active",
    )

    search_fields = (
        "customer_id",
        "email",
        "phone",
        "first_name",
        "last_name",
    )

    readonly_fields = (
        "customer_id",
        "last_login",
        "date_joined",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "customer_id",
                    "email",
                    "password",
                )
            },
        ),
        (
            "Personal information",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "phone",
                )
            },
        ),
        (
            "Bokku Mart",
            {
                "fields": (
                    "role",
                    "is_email_verified",
                    "is_phone_verified",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Important dates",
            {
                "fields": (
                    "last_login",
                    "date_joined",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "phone",
                    "first_name",
                    "last_name",
                    "role",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )


@admin.register(Address)
class AddressAdmin(ModelAdmin):
    list_display = (
        "recipient_name",
        "user",
        "phone",
        "city",
        "state",
        "is_default",
        "created_at",
    )

    list_filter = (
        "state",
        "city",
        "is_default",
    )

    search_fields = (
        "recipient_name",
        "user__customer_id",
        "user__email",
        "phone",
        "address_line",
        "city",
        "state",
    )

    autocomplete_fields = ("user",)

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )


admin.site.unregister(Group)


@admin.register(Group)
class CustomGroupAdmin(GroupAdmin, ModelAdmin):
    pass
