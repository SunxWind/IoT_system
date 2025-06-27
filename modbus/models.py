from django.db import models

class ModbusDevice(models.Model):
    name = models.CharField(max_length=100)
    host = models.CharField(max_length=100)
    port = models.PositiveIntegerField(default=5020)
    slave_id = models.PositiveIntegerField(default=1)
    register_address = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=False)
    is_running = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.host}:{self.port})"

