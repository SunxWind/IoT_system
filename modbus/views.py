import os
from dotenv import load_dotenv
from pymongo import MongoClient
from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import ModbusDevice
from .serializers import ModbusDeviceSerializer
from .modbus_server import start_server, stop_server, is_server_running
from .services import start_client, stop_client

# Load environment variables from .env file
load_dotenv()

# Load MongoDB connection settings
MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB = os.getenv('MONGO_DB_NAME')
MONGO_COLLECTION = os.getenv('MODBUS_COLLECTION_NAME')


class ModbusDeviceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for performing CRUD operations on ModbusDevice model.
    Exposes endpoints for create, retrieve, update, delete and list.
    """
    queryset = ModbusDevice.objects.all()
    serializer_class = ModbusDeviceSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def server_status(request):
    """
    Return the current status of the Modbus server.
    Used to check if the server is running.
    """
    return Response({"running": is_server_running()})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_modbus_server(request):
    """
    Start the Modbus TCP server if it's not already running.
    """
    if is_server_running():
        return Response({'message': 'Server is already running'}, status=status.HTTP_400_BAD_REQUEST)

    start_server()
    return Response({'message': 'Modbus server started'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def stop_modbus_server(request):
    """
    Stop the Modbus TCP server if it's currently running.
    """
    if not is_server_running():
        return Response({'message': 'Server is not running'}, status=status.HTTP_400_BAD_REQUEST)

    stop_server()
    return Response({'message': 'Modbus server stopped'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_devices(request):
    """
    Return a list of all Modbus devices with full metadata.
    """
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
@permission_classes([IsAuthenticated])
def start_modbus_device(request, pk):
    """
    Start the Modbus client for a specific device by primary key.
    """
    try:
        device = ModbusDevice.objects.get(pk=pk)
        start_client(device)
        return Response({"status": "started"})
    except ModbusDevice.DoesNotExist:
        return Response({"error": "Device not found"}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def stop_modbus_device(request, pk):
    """
    Stop the Modbus client for a specific device by primary key.
    """
    try:
        device = ModbusDevice.objects.get(pk=pk)
        stop_client(device)
        return Response({"status": "stopped"})
    except ModbusDevice.DoesNotExist:
        return Response({"error": "Device not found"}, status=404)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_active_devices(request):
    """
    Return a list of all currently active devices (is_active = True).
    """
    active_devices = ModbusDevice.objects.filter(is_active=True)
    data = [{'id': d.id, 'name': d.name} for d in active_devices]
    return JsonResponse(data, safe=False)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fetch_device_logs(request, device_id):
    """
    Fetch the latest 20 log entries for a given device from MongoDB.
    The logs include timestamp and value, sorted by newest first.

    Args:
        device_id (int): The primary key of the device to retrieve logs for.

    Returns:
        JsonResponse: List of logs or error message.
    """
    try:
        # Connect to MongoDB and select the collection
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB]
        collection = db[MONGO_COLLECTION]

        # Fetch the latest 20 log records for the device
        logs = list(collection.find({'device_id': device_id}).sort('timestamp', -1).limit(20))

        # Format ObjectId and round timestamps for frontend readability
        for log in logs:
            log['_id'] = str(log['_id'])  # Convert ObjectId to string
            log['timestamp'] = round(log['timestamp'], 2)

        return JsonResponse(logs, safe=False)

    except Exception as e:
        # Return server error response with exception details
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
