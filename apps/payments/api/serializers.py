from abc import ABC

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


class PurchaseSerializer(serializers.Serializer):
    gateway = serializers.PrimaryKeyRelatedField(queryset=Gateway.objects.filter(is_enable=True))
    order = serializers.PrimaryKeyRelatedField(
        queryset=Order.objects.filter(is_paid=None, properties__redirect_url__isnull=False)
    )

    def validate_gateway(self, obj):
        request = self.context['request']
        if not obj.services.filter(id=request.auth['service'].id).exists():
            raise ValidationError(
                detail={'detail': _("service and gateway does not match!")}
            )
        return obj

    def validate_order(self, obj):
        request = self.context['request']

        if obj.service != request.auth['service']:
            raise ValidationError(
                detail={'detail': _("order and service does not match!")}
            )
        return obj

    def validate(self, attrs):
        gateway = attrs['gateway']
        order = attrs['order']
        if order.gateway != gateway:
            raise ValidationError(
                detail={'detail': _("order and gateway does not match!")}
            )
        return attrs

    def create(self, validated_data):
        raise NotImplementedError('must be implemented')

    def update(self, instance, validated_data):
        raise NotImplementedError('must be implemented')


class VerifySerializer(serializers.Serializer):
    purchase_token = serializers.CharField(max_length=100)
    order = serializers.PrimaryKeyRelatedField(
        queryset=Order.objects.filter(is_paid=None)
    )

    def validate_order(self, obj):
        request = self.context['request']

        if obj.service != request.auth['service']:
            raise ValidationError(
                detail={'detail': _("order and service does not match!")}
            )
        if obj.gateway.code != Gateway.FUNCTION_BAZAAR:
            raise ValidationError(
                detail={'detail': _("invalid gateway!")}
            )
        return obj

    def create(self, validated_data):
        raise NotImplementedError('must be implemented')

    def update(self, instance, validated_data):
        raise NotImplementedError('must be implemented')
