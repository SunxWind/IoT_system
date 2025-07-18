from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (ModbusDeviceViewSet, list_devices, server_status, start_modbus_server, stop_modbus_server, start_modbus_device,
                    stop_modbus_device, fetch_device_logs, get_active_devices)


router = DefaultRouter()
router.register(r'', ModbusDeviceViewSet)

# Urls for main Modbus endpoints

urlpatterns = [
    # Listing of active Modbus devices
    path('api/devices/', list_devices, name='list_devices'),
    # Showing the Modbus server status (Stopped/Running)
    path('api/server/status/', server_status, name='server_status'),
    # Starting Modbus server
    path('api/server/start/', start_modbus_server, name='start_modbus_server'),
    # Stopping Modbus server
    path('api/server/stop/', stop_modbus_server, name='stop_modbus_server'),
    # Starting a Modbus (parameter - serial number) device
    path('api/devices/<int:pk>/start/', start_modbus_device, name='start_modbus_device'),
    # Stopping a Modbus (parameter - serial number) device
    path('api/devices/<int:pk>/stop/', stop_modbus_device, name='stop_modbus_device'),
    # Getting active Modbus devices
    path('api/devices/active/', get_active_devices, name='get_active_devices'),
    # Showing data log for a chosen Modbus device
    path('api/devices/<int:device_id>/logs/', fetch_device_logs, name='device-logs'),
    ]

urlpatterns += router.urls
