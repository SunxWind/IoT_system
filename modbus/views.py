import os
from dotenv import load_dotenv
from pymongo import MongoClient
from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import ModbusDevice
from .serializers import ModbusDeviceSerializer
from .modbus_server import start_server, stop_server, is_server_running
from .services import start_client, stop_client


load_dotenv()

MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB = os.getenv('MONGO_DB_NAME')
MONGO_COLLECTION = os.getenv('MODBUS_COLLECTION_NAME')


class ModbusDeviceViewSet(viewsets.ModelViewSet):
    """ViewSet for performing CRUD operations on device metadata."""
    queryset = ModbusDevice.objects.all()
    serializer_class = ModbusDeviceSerializer


@api_view(['GET'])
def server_status(request):
    return Response({"running": is_server_running()})


@api_view(['POST'])
def start_modbus_server(request):
    if is_server_running():
        return Response({'message': 'Server is already running'}, status=status.HTTP_400_BAD_REQUEST)

    start_server()
    return Response({'message': 'Modbus server started'}, status=status.HTTP_200_OK)


@api_view(['POST'])
def stop_modbus_server(request):
    if not is_server_running():
        return Response({'message': 'Server is not running'}, status=status.HTTP_400_BAD_REQUEST)

    stop_server()
    return Response({'message': 'Modbus server stopped'}, status=status.HTTP_200_OK)


@api_view(['GET'])
def list_devices(request):
    devices = ModbusDevice.objects.all()
    data = [
        {
            "id": device.id,
            "name": device.name,
            "host": device.host,
            "port": device.port,
            "slave_id": device.slave_id,
            "register_address": device.register_address,
            "is_active": device.is_active,
            "is_running": device.is_running,
        }
        for device in devices
    ]
    return Response(data)


@api_view(['POST'])
def start_modbus_device(request, pk):
    try:
        device = ModbusDevice.objects.get(pk=pk)
        start_client(device)
        return Response({"status": "started"})
    except ModbusDevice.DoesNotExist:
        return Response({"error": "Device not found"}, status=404)


@api_view(['POST'])
def stop_modbus_device(request, pk):
    try:
        device = ModbusDevice.objects.get(pk=pk)
        stop_client(device)
        return Response({"status": "stopped"})
    except ModbusDevice.DoesNotExist:
        return Response({"error": "Device not found"}, status=404)


@api_view(['GET'])
def get_active_devices(request):
    active_devices = ModbusDevice.objects.filter(is_active=True)
    data = [{'id': d.id, 'name': d.name} for d in active_devices]
    return JsonResponse(data, safe=False)


@api_view(['GET'])
def fetch_device_logs(request, device_id):
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB]
        collection = db[MONGO_COLLECTION]

        logs = list(collection.find({'device_id': device_id}).sort('timestamp', -1).limit(20))  # latest 20

        for log in logs:
            log['_id'] = str(log['_id'])  # Convert ObjectId to string
            log['timestamp'] = round(log['timestamp'], 2)

        return JsonResponse(logs, safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)