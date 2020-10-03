from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from ..models import Gateway, Order


class ServiceGatewaySerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='gateway.id')
    image_url = serializers.SerializerMethodField()
    display_name = serializers.ReadOnlyField(source='gateway.display_name')
    code = serializers.ReadOnlyField(source='gateway.code')

    class Meta:
        model = Gateway
        fields = ('id', 'display_name', 'code', 'image_url')

    def get_image_url(self, obj):
        request = self.context['request']
        return request.build_absolute_uri(obj.image.url)


class OrderSerializer(serializers.ModelSerializer):
    gateways = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            'price', 'service_reference', 'is_paid', 'properties', 'gateways'
        )

    def get_gateways(self, obj):
        service = self.context['request'].auth['service']
        return service.gateways.filter(is_enable=True)

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
                detail={'detail': _("Order with this service and service reference already exists!")}
            )
        return attrs


class PurchaseSerializer(serializers.Serializer):
    gateway = serializers.PrimaryKeyRelatedField(queryset=Gateway.objects.filter(is_enable=True))
    order = serializers.CharField(max_length=40)

    def validate_gateway(self, obj):
        request = self.context['request']
        if not obj.services.filter(id=request.auth['service'].id).exists():
            raise ValidationError(
                detail={'detail': _("service and gateway does not match!")}
            )
        return obj

    def validate_order(self, value):
        request = self.context['request']
        try:
            order = Order.objects.get(service=request.auth['service'], service_reference=value)
            return order
        except Order.DoesNotExist:
            raise ValidationError(
                detail={'detail': _("order and service does not match!")}
            )

    def create(self, validated_data):
        raise NotImplementedError('must be implemented')

    def update(self, instance, validated_data):
        raise NotImplementedError('must be implemented')


class VerifySerializer(serializers.Serializer):
    purchase_token = serializers.CharField(max_length=100)
    order = serializers.CharField(max_length=40)

    def validate_order(self, value):
        request = self.context['request']
        try:
            order = Order.objects.get(service=request.auth['service'], service_reference=value, is_paid=None)
        except Order.DoesNotExist:
            raise ValidationError(
                detail={'detail': _("order and service does not match!")}
            )
        if order.gateway.code != Gateway.FUNCTION_BAZAAR:
            raise ValidationError(
                detail={'detail': _("invalid gateway!")}
            )
        return order

    def create(self, validated_data):
        raise NotImplementedError('must be implemented')

    def update(self, instance, validated_data):
        raise NotImplementedError('must be implemented')
