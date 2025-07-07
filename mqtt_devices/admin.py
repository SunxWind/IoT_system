from django.contrib import admin
from .models import MQTTDevice


@admin.register(MQTTDevice)
class MQTTDeviceAdmin(admin.ModelAdmin):
    """
    Admin interface for the Device model.
    Allows managing device metadata via Django admin UI.
    """
    list_display = ('name', 'serial_number', 'location')  # Columns shown in list view
    search_fields = ('name', 'serial_number', 'location')  # Enable admin search
