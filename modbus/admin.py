from django.contrib import admin
from .models import ModbusDevice

@admin.register(ModbusDevice)
class ModbusDeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "host", "port", "slave_id", "register_address", "is_active", "is_running")
    actions = ['start_modbus_client', 'stop_modbus_client', 'start_modbus_server', 'stop_modbus_server']
