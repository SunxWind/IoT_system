from rest_framework import serializers
from .models import MQTTDevice


class MQTTDeviceSerializer(serializers.ModelSerializer):
    """Serializer for the MQTT Device model. Converts MQTTDevice model instances to JSON."""
    class Meta:
        model = MQTTDevice
        fields = '__all__'
