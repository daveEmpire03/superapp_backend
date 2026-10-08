from math import radians,sin,cos,sqrt,atan2
from rest_framework import generics, permissions
from .models import Store
from .serializers import StoreSerializer

def distance_km(lat1,lon1,lat2,lon2):
    r=6371.0
    dlat=radians(lat2-lat1); dlon=radians(lon2-lon1)
    a=sin(dlat/2)**2+cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return r*2*atan2(sqrt(a),sqrt(1-a))

class StoreListView(generics.ListAPIView):
    serializer_class=StoreSerializer
    permission_classes=[permissions.AllowAny]
    pagination_class=None
    def get_queryset(self):
        return Store.objects.filter(is_active=True).order_by("name")
    def list(self,request,*args,**kwargs):
        response=super().list(request,*args,**kwargs)
        try: lat=float(request.query_params["lat"]); lon=float(request.query_params["lng"])
        except (KeyError,ValueError,TypeError): return response
        for item in response.data:
            if item.get("latitude") and item.get("longitude"):
                item["distance_km"]=round(distance_km(lat,lon,float(item["latitude"]),float(item["longitude"])),2)
        response.data.sort(key=lambda x:x.get("distance_km",float("inf")))
        return response
