from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class MQTTDevice(models.Model):
    """Represents metadata about a device stored in PostgreSQL."""
    name = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, unique=True)
    slave_id = models.IntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(247)])
    location = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    mqtt_command_topic = models.CharField(max_length=255, default="mqtt_devices/{serial_number}/command")
    mqtt_status_topic = models.CharField(max_length=255, default="mqtt_devices/{serial_number}/status")

    def save(self, *args, **kwargs):
        # Auto-generate MQTT topics if using {serial_number} template
        if "{serial_number}" in self.mqtt_command_topic:
            self.mqtt_command_topic = f"mqtt_devices/{self.serial_number}/command"

        if "{serial_number}" in self.mqtt_status_topic:
            self.mqtt_status_topic = f"mqtt_devices/{self.serial_number}/status"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} (Modbus: {self.slave_id}, MQTT: {self.serial_number})"
