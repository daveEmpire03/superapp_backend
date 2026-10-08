from rest_framework.permissions import BasePermission
class IsAdminOrManager(BasePermission):
    def has_permission(self,request,view): return request.user.is_authenticated and (request.user.is_staff or request.user.role in {'ADMIN','STORE_MANAGER'})
class IsStaffMember(BasePermission):
    def has_permission(self,request,view): return request.user.is_authenticated and (request.user.is_staff or request.user.role in {'ADMIN','STORE_MANAGER','STAFF'})
class IsRider(BasePermission):
    def has_permission(self,request,view): return request.user.is_authenticated and request.user.role=='RIDER'
