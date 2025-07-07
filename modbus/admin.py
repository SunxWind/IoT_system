from django.contrib import admin
from .models import ModbusDevice


# Registration of Modbus device model in the Djungo admin panel for visualization and administration
@admin.register(ModbusDevice)
class ModbusDeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "host", "port", "slave_id", "register_address", "is_active", "is_running")
    actions = ['start_modbus_client', 'stop_modbus_client', 'start_modbus_server', 'stop_modbus_server']
