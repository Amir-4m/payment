from django.urls import path
from rest_framework import routers

from .views import ServiceGatewayViewSet, OrderViewSet

urlpatterns = [

]
router = routers.DefaultRouter()
router.register('gateways', ServiceGatewayViewSet)
router.register('orders', OrderViewSet)

urlpatterns += router.urls
