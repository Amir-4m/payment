from rest_framework import routers

from .views import ServiceGatewayViewSet, OrderViewSet, PurchaseAPIView

urlpatterns = [
]

router = routers.DefaultRouter()
router.register('gateways', ServiceGatewayViewSet)
router.register('orders', OrderViewSet)
router.register('purchase', PurchaseAPIView, basename='purchase')

urlpatterns += router.urls
