from django.db import transaction

from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Cart, CartItem
from .serializers import (
    AddCartItemSerializer,
    CartSerializer,
    UpdateCartItemSerializer,
)


def get_user_cart(user):
    cart, _ = Cart.objects.get_or_create(
        user=user,
    )

    return cart


def get_cart_queryset():
    return Cart.objects.select_related("store").prefetch_related(
        "items__inventory__product",
        "items__inventory__store",
    )


class MyCartView(RetrieveAPIView):
    serializer_class = CartSerializer

    def get_object(self):
        cart = get_user_cart(
            self.request.user,
        )

        return get_cart_queryset().get(
            id=cart.id,
        )


class AddCartItemView(APIView):

    @transaction.atomic
    def post(self, request):
        serializer = AddCartItemSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        # Lock inventory to recheck sellable stock after concurrent reservations.
        inventory = serializer.validated_data["inventory"]
        inventory = type(inventory).objects.select_for_update().get(pk=inventory.pk)

        quantity = serializer.validated_data["quantity"]

        if (
            not inventory.is_available
            or not inventory.store.is_active
            or not inventory.product.is_active
            or quantity > inventory.available_quantity
        ):
            return Response(
                {"success": False, "error": {"quantity": "Insufficient available stock."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart = Cart.objects.select_for_update().filter(user=request.user).first()

        if cart is None:
            cart = Cart.objects.create(
                user=request.user,
            )

        # A cart can contain products from only one store.
        if cart.store_id is not None and cart.store_id != inventory.store_id:
            return Response(
                {
                    "success": False,
                    "error": {
                        "store": (
                            "Your cart contains products "
                            "from another store. Clear the "
                            "cart before shopping from a "
                            "different store."
                        )
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if cart.store_id is None:
            cart.store = inventory.store
            cart.save(
                update_fields=[
                    "store",
                    "updated_at",
                ]
            )

        cart_item = (
            CartItem.objects.select_for_update()
            .filter(
                cart=cart,
                inventory=inventory,
            )
            .first()
        )

        if cart_item:
            new_quantity = cart_item.quantity + quantity

            if new_quantity > inventory.available_quantity:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "quantity": (
                                "Only "
                                f"{inventory.available_quantity} "
                                "units are currently "
                                "available."
                            )
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            cart_item.quantity = new_quantity
            cart_item.save(
                update_fields=[
                    "quantity",
                    "updated_at",
                ]
            )

        else:
            CartItem.objects.create(
                cart=cart,
                inventory=inventory,
                quantity=quantity,
            )

        cart = get_cart_queryset().get(
            id=cart.id,
        )

        return Response(
            {
                "success": True,
                "message": "Product added to cart.",
                "data": CartSerializer(cart).data,
            },
            status=status.HTTP_200_OK,
        )


class UpdateCartItemView(APIView):

    @transaction.atomic
    def patch(self, request, item_id):
        cart = Cart.objects.select_for_update().filter(user=request.user).first()

        if cart is None:
            return Response(
                {
                    "success": False,
                    "error": {"cart": "Cart not found."},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            cart_item = (
                CartItem.objects.select_for_update()
                .select_related(
                    "inventory",
                    "inventory__product",
                )
                .get(
                    id=item_id,
                    cart=cart,
                )
            )

        except CartItem.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": {"item": "Cart item not found."},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Serialize stock checks against checkout reservations and stock changes.
        inventory = type(cart_item.inventory).objects.select_for_update().get(
            pk=cart_item.inventory_id
        )
        cart_item.inventory = inventory

        serializer = UpdateCartItemSerializer(
            data=request.data,
            context={
                "cart_item": cart_item,
            },
        )

        serializer.is_valid(
            raise_exception=True,
        )

        cart_item.quantity = serializer.validated_data["quantity"]

        cart_item.save(
            update_fields=[
                "quantity",
                "updated_at",
            ]
        )

        cart = get_cart_queryset().get(
            id=cart.id,
        )

        return Response(
            {
                "success": True,
                "message": "Cart updated.",
                "data": CartSerializer(cart).data,
            }
        )


class RemoveCartItemView(APIView):

    @transaction.atomic
    def delete(self, request, item_id):
        cart = Cart.objects.select_for_update().filter(user=request.user).first()

        if cart is None:
            return Response(
                {
                    "success": False,
                    "error": {"cart": "Cart not found."},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        deleted_count, _ = CartItem.objects.filter(
            id=item_id,
            cart=cart,
        ).delete()

        if deleted_count == 0:
            return Response(
                {
                    "success": False,
                    "error": {"item": "Cart item not found."},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if not cart.items.exists():
            cart.store = None
            cart.save(
                update_fields=[
                    "store",
                    "updated_at",
                ]
            )

        cart = get_cart_queryset().get(
            id=cart.id,
        )

        return Response(
            {
                "success": True,
                "message": "Product removed from cart.",
                "data": CartSerializer(cart).data,
            }
        )


class ClearCartView(APIView):

    @transaction.atomic
    def delete(self, request):
        cart = Cart.objects.select_for_update().filter(user=request.user).first()

        if cart is None:
            return Response(
                {
                    "success": True,
                    "message": "Cart is already empty.",
                }
            )

        cart.items.all().delete()

        cart.store = None

        cart.save(
            update_fields=[
                "store",
                "updated_at",
            ]
        )

        return Response(
            {
                "success": True,
                "message": "Cart cleared successfully.",
            }
        )
