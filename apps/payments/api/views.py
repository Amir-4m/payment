from rest_framework import viewsets, mixins, views
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, ParseError
from rest_framework.response import Response

from ..models import Gateway
from .serializers import GatewaySerializer
from ...services.authentications import ServiceAuthentication


class ServiceGatewayViewSet(viewsets.GenericViewSet, mixins.ListModelMixin):
    queryset = Gateway.objects.all()
    serializer_class = GatewaySerializer
    authentication_classes = (ServiceAuthentication,)

    def get_queryset(self):
        service = self.request.auth['service']
        qs = super(ServiceGatewayViewSet, self).get_queryset()
        return qs.filter(is_enable=True, services=service)
