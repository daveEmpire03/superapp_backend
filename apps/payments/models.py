from django.db import models
from core.models import TimeStampedModel
from apps.orders.models import Order
class Payment(TimeStampedModel):
    class Status(models.TextChoices): INITIALIZED="INITIALIZED","Initialized"; SUCCESS="SUCCESS","Success"; FAILED="FAILED","Failed"; REFUNDED="REFUNDED","Refunded"
    order=models.ForeignKey(Order,on_delete=models.PROTECT,related_name="payments")
    provider=models.CharField(max_length=30,default="FLUTTERWAVE")
    tx_ref=models.CharField(max_length=120,unique=True)
    provider_transaction_id=models.CharField(max_length=120,blank=True)
    amount=models.DecimalField(max_digits=12,decimal_places=2)
    currency=models.CharField(max_length=3,default="NGN")
    status=models.CharField(max_length=20,choices=Status.choices,default=Status.INITIALIZED)
    raw_response=models.JSONField(default=dict,blank=True)
