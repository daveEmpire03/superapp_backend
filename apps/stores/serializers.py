from rest_framework import serializers
from .models import Store
class StoreSerializer(serializers.ModelSerializer):
    distance_km=serializers.FloatField(read_only=True,required=False)
    class Meta: model=Store; fields="__all__"
