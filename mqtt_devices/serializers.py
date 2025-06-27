from rest_framework import serializers
from .models import MQTTDevice

class MQTTDeviceSerializer(serializers.ModelSerializer):
    """Serializer for the Device model."""
    class Meta:
        model = MQTTDevice
        fields = '__all__'
