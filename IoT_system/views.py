from django.shortcuts import render


# Index page view
def index(request):
    return render(request, 'base.html')


# MQTT dashboard view
def mqtt(request):
    return render(request, 'mqtt.html')


# Modbus dashboard view
def modbus(request):
    return render(request, 'modbus.html')