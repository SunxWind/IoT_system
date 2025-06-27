from django.shortcuts import render


def index(request):
    return render(request, 'base.html')

def mqtt(request):
    return render(request, 'mqtt.html')

def modbus(request):
    return render(request, 'modbus.html')