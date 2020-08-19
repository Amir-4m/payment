from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from ..models import Gateway, Order, ServiceGateway


class GatewaySerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Gateway
        fields = ('id', 'display_name', 'image_url')

    def get_image_url(self, obj):
        return obj.image.url


class OrderSerializer(serializers.ModelSerializer):
    service_gateway = serializers.PrimaryKeyRelatedField(queryset=Gateway.objects.all())

    class Meta:
        model = Order
        fields = (
            'service_gateway', 'price', 'service_reference',
            'invoice_number', 'reference_id', 'is_paid', 'properties'
        )

    def validate_service_gateway(self, obj):
        request = self.context['request']
        try:
            service_gateway = ServiceGateway.objects.get(gateway=obj, service=request.auth['service'])
            if service_gateway.is_enable is False:
                raise ValidationError(detail={'detail': _("Gateway is not available!")})
            return service_gateway
        except ServiceGateway.DoesNotExist:
            raise ValidationError(detail={'detail': _("Service gateway does not exists!")})

    def validate_service_reference(self, value):
        if Order.objects.filter(service_reference=value).exists():
            raise ValidationError(detail={'detail': _("Order with this reference already exists!")})
