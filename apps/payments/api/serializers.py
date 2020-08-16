from rest_framework import serializers

from ..models import Gateway


class GatewaySerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Gateway
        fields = ('id', 'display_name', 'image_url')

    def get_image_url(self, obj):
        return obj.image.url
