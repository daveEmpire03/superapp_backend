from django.conf import settings
from django.db import models
from core.models import TimeStampedModel
from apps.stores.models import Store
from apps.inventory.models import StoreInventory
class Cart(TimeStampedModel):
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="cart")
    store=models.ForeignKey(Store,on_delete=models.PROTECT,null=True,blank=True)
class CartItem(TimeStampedModel):
    cart=models.ForeignKey(Cart,on_delete=models.CASCADE,related_name="items")
    inventory=models.ForeignKey(StoreInventory,on_delete=models.PROTECT)
    quantity=models.PositiveIntegerField(default=1)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["cart","inventory"],name="unique_cart_inventory")]
