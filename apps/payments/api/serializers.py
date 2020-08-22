from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from ..models import Gateway, Order


class GatewaySerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Gateway
        fields = ('id', 'display_name', 'image_url')

    def get_image_url(self, obj):
        return obj.image.url


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = (
            'gateway', 'price', 'service_reference', 'is_paid'
        )

    def validate_gateway(self, obj):
        service = self.context['request'].auth['service']
        if not obj.services.filter(id=service.id).exists():
            raise ValidationError(detail={'detail': _("service and gateway does not match!")})
        return obj

    def validate(self, attrs):
        request = self.context['request']
        service_reference = attrs.get('service_reference')
        if Order.objects.filter(service=request.auth['service'], service_reference=service_reference).exists():
            raise ValidationError(
                detail={'detail': _("Order with this service and service reference  already exists!")}
            )
        return attrs
