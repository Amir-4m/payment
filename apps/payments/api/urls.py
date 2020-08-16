from django.urls import path
from rest_framework import routers

from .views import ServiceGatewayViewSet

urlpatterns = [

]
router = routers.DefaultRouter()
router.register('gateways', ServiceGatewayViewSet)

urlpatterns += router.urls
