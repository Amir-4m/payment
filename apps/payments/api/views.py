from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, mixins

from ..models import Gateway, Order
from .serializers import GatewaySerializer, OrderSerializer
from apps.services.api.authentications import ServiceAuthentication
from ..pagination import OrderPagination
from ...services.api.permissions import ServicePermission


class ServiceGatewayViewSet(viewsets.GenericViewSet, mixins.ListModelMixin):
    queryset = Gateway.objects.all()
    serializer_class = GatewaySerializer
    authentication_classes = (ServiceAuthentication,)
    permission_classes = (ServicePermission,)

    def get_queryset(self):
        service = self.request.auth['service']
        qs = super(ServiceGatewayViewSet, self).get_queryset()
        return qs.filter(is_enable=True, services=service)


class OrderViewSet(
    viewsets.GenericViewSet,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin
):
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['created_time', 'is_paid', 'service']
    pagination_class = OrderPagination
    lookup_field = 'service_reference'
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    authentication_classes = (ServiceAuthentication,)
    permission_classes = (ServicePermission,)

    def perform_create(self, serializer):
        serializer.save(service=self.request.auth['service'])
