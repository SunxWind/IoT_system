from rest_framework import serializers
from .models import ModbusDevice


class ModbusDeviceSerializer(serializers.ModelSerializer):
    """Serializer for the Modbus Device model. Converts ModbusDevice model instances to JSON."""
    class Meta:
        model = ModbusDevice
        fields = '__all__'
