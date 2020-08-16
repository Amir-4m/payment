from rest_framework import viewsets, mixins

from ..models import Gateway, Order
from .serializers import GatewaySerializer, OrderSerializer
from ...services.authentications import ServiceAuthentication


class ServiceGatewayViewSet(viewsets.GenericViewSet, mixins.ListModelMixin):
    queryset = Gateway.objects.all()
    serializer_class = GatewaySerializer
    authentication_classes = (ServiceAuthentication,)

    def get_queryset(self):
        service = self.request.auth['service']
        qs = super(ServiceGatewayViewSet, self).get_queryset()
        return qs.filter(is_enable=True, services=service)


class OrderViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    authentication_classes = (ServiceAuthentication,)
