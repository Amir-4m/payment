from urllib.parse import urlencode

from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.reverse import reverse

from ..models import Gateway, Order
from .serializers import GatewaySerializer, OrderSerializer, PurchaseSerializer, VerifySerializer
from apps.services.api.authentications import ServiceAuthentication
from ..pagination import OrderPagination
from ..services import BazaarService
from ...services.api.permissions import ServicePermission


class GatewayViewSet(viewsets.GenericViewSet, mixins.ListModelMixin):
    queryset = Gateway.objects.all()
    serializer_class = GatewaySerializer
    authentication_classes = (ServiceAuthentication,)
    permission_classes = (ServicePermission,)

    def get_queryset(self):
        service = self.request.auth['service']
        qs = super(GatewayViewSet, self).get_queryset()
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


class PurchaseAPIView(viewsets.ViewSet):
    authentication_classes = (ServiceAuthentication,)
    permission_classes = (ServicePermission,)

    @action(methods=['post'], detail=False)
    def gateway(self, request, *args, **kwargs):
        serializer = PurchaseSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        return Response(
            {
                'gateway_url': reverse(
                    'bank-gateway',
                    request=request,
                    kwargs={"order_id": serializer.validated_data['order'].id})
            }
        )

    @action(methods=['post'], detail=False)
    def verify(self, request, *args, **kwargs):
        data = request.data
        serializer = VerifySerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        order = serializer.validated_data['order']
        with transaction.atomic():
            payment = Order.objects.select_related(
                'service',
                'gateway'
            ).select_for_update().get(
                id=order.id
            )
            purchase_verified = BazaarService.verify_purchase(
                order=payment,
                purchase_token=serializer.validated_data['purchase_token']
            )

        return Response({'purchase_verified': purchase_verified})
