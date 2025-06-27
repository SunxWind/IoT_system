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

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='index'),
    path('mqtt/', mqtt, name='mqtt'),
    path('mqtt/api/', include('mqtt_clients.urls')),
    path('modbus/', modbus, name='modbus'),
    path('modbus/', include('modbus.urls')),
    path('mqtt/api/', include('data_api.urls')),
    path('mqtt/', include('mqtt_devices.urls')),
]
