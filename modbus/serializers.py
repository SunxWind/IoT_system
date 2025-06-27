from rest_framework import serializers
from .models import ModbusDevice

class ModbusDeviceSerializer(serializers.ModelSerializer):
    """Serializer for the Device model."""
    class Meta:
        model = ModbusDevice
        fields = '__all__'
