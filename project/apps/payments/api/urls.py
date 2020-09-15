from rest_framework import routers

from .views import GatewayViewSet, OrderViewSet, PurchaseAPIView

urlpatterns = [
]

router = routers.DefaultRouter()
router.register('gateways', GatewayViewSet)
router.register('orders', OrderViewSet)
router.register('purchase', PurchaseAPIView, basename='purchase')

urlpatterns += router.urls
