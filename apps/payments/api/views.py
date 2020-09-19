from django.db import transaction
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.reverse import reverse

from apps.services.api.authentications import ServiceAuthentication
from ..models import Gateway, Order
from .serializers import GatewaySerializer, OrderSerializer, PurchaseSerializer, VerifySerializer
from ..pagination import OrderPagination
from ..services import BazaarService
from ..swagger_schemas import ORDER_POST_DOCS, PURCHASE_GATEWAY_DOCS, PURCHASE_VERIFY_DOCS_RESPONSE, \
    PURCHASE_GATEWAY_DOCS_RESPONSE
from ...services.api.permissions import ServicePermission


class GatewayViewSet(viewsets.GenericViewSet, mixins.ListModelMixin):
    """
    Shows a list of available gateways for the specific service.
    """
    queryset = Gateway.objects.all()
    serializer_class = GatewaySerializer
    authentication_classes = (ServiceAuthentication,)
    permission_classes = (ServicePermission,)

    def get_queryset(self):
        service = self.request.auth['service']
        qs = super(GatewayViewSet, self).get_queryset()
        return qs.filter(is_enable=True, services=service)


@method_decorator(name='list', decorator=swagger_auto_schema(
    operation_description="Get a list of submitted orders by service.",
    responses={"200": 'Successful'}
))
@method_decorator(name='create', decorator=swagger_auto_schema(
    operation_description="Create a order for the service.",
    request_body=ORDER_POST_DOCS
))
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

    @method_decorator(name='gateway', decorator=swagger_auto_schema(
        operation_description="Return bank gateway url for the requested order.",
        request_body=PURCHASE_GATEWAY_DOCS,
        responses={200: PURCHASE_GATEWAY_DOCS_RESPONSE}

    ))
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

    @method_decorator(name='verify', decorator=swagger_auto_schema(
        operation_description="Verify payment status of the requested order and return its status. (only PSP gateways such as bazaar, etc ...)",
        request_body=PURCHASE_GATEWAY_DOCS,
        responses={200: PURCHASE_VERIFY_DOCS_RESPONSE}
    ))
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
