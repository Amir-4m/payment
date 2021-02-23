from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from ..models import Gateway, Order, ServiceGateway


class ServiceGatewaySerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='gateway.id')
    image_url = serializers.SerializerMethodField()
    display_name = serializers.ReadOnlyField(source='gateway.display_name')
    code = serializers.ReadOnlyField(source='gateway.code')

    class Meta:
        model = ServiceGateway
        fields = ('id', 'display_name', 'code', 'image_url')

    def get_image_url(self, obj):
        request = self.context['request']
        return request.build_absolute_uri(obj.image.url)


class OrderSerializer(serializers.ModelSerializer):
    gateways = serializers.SerializerMethodField()
    redirect_url = serializers.CharField(write_only=True, required=False)
    # TODO: needs validation
    phone_number = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Order
        fields = (
            'price', 'service_reference',
            'properties', 'redirect_url', 'phone_number',
            'transaction_id', 'is_paid', 'gateway', 'gateways'
        )
        read_only_fields = ('transaction_id', 'is_paid', 'gateway')

    def get_gateways(self, obj):
        request = self.context['request']
        service = self.context['request'].auth['service']
        _gateway_list = service.service_gateways.filter(is_enable=True)
        return ServiceGatewaySerializer(_gateway_list, many=True, context={'request': request}).data

    def validate_gateway(self, obj):
        service = self.context['request'].auth['service']
        if not obj.services.filter(id=service.id).exists():
            raise ValidationError(detail={'detail': _("service and gateway does not match!")})
        return obj

    def validate(self, attrs):
        request = self.context['request']
        service_reference = attrs.get('service_reference')
        qs = Order.objects.filter(
            service=request.auth['service'],
            service_reference=service_reference,
            is_paid__isnull=False
        )
        if qs.exists():
            raise ValidationError(
                detail={'detail': _("Order with this service and service reference has been paid already!")}
            )
        return attrs

    def create(self, validated_data):
        price = validated_data.get('price')
        service_reference = validated_data.get('service_reference')
        properties = validated_data.get('properties', {})
        if validated_data.get('redirect_url'):
            properties.update({'redirect_url': validated_data['redirect_url']})
        if validated_data.get('phone_number'):
            properties.update({'phone_number': validated_data['phone_number']})

        order, _created = Order.objects.get_or_create(
            service_reference=service_reference,
            service=validated_data['service'],
            defaults={
                'price': price,
                'properties': properties,
            }
        )
        return order


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
        except Order.DoesNotExist:
            raise ValidationError(
                detail={'detail': _("order and service does not match!")}
            )
        return order

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


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
        pass

    def update(self, instance, validated_data):
        pass
