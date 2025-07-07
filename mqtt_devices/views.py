from rest_framework import viewsets
from .models import MQTTDevice
from .serializers import MQTTDeviceSerializer


class MQTTDeviceViewSet(viewsets.ModelViewSet):
    """ViewSet for performing CRUD operations on device metadata."""
    queryset = MQTTDevice.objects.all()
    serializer_class = MQTTDeviceSerializer