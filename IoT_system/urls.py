"""
URL configuration for IoT_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from .views import index, mqtt, modbus


# Main Django urls
urlpatterns = [
    path('admin/', admin.site.urls),
    # Url for index page
    path('', index, name='index'),
    # Url for MQTT dashboard page
    path('mqtt/', mqtt, name='mqtt'),
    # Including urls for MQTT endpoints
    path('mqtt/api/', include('mqtt_clients.urls')),
    # Url for Modbus dashboard page
    path('modbus/', modbus, name='modbus'),
    # Including urls for Modbus endpoints
    path('modbus/', include('modbus.urls')),
    # Including MQTT endpoints urls for MQTTDataMongoView and SendMQTTCommand view
    path('mqtt/api/', include('data_api.urls')),
    # Including endpoints urls for CRUD operations for MQTT devices
    path('mqtt/', include('mqtt_devices.urls')),
]
