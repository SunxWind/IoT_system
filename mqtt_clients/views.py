import time
import threading
from django.http import JsonResponse
from rest_framework.decorators import api_view
from .mqtt_publisher import start_publisher, stop_publisher, get_publisher_status
from .mqtt_subscriber import MQTTSubscriber

subscriber_instance = None

@api_view(['POST'])
def start_mqtt_publisher(request):
    started = start_publisher()
    return JsonResponse({'status': 'started' if started else 'already_running'})

@api_view(['POST'])
def stop_mqtt_publisher(request):
    stop_publisher()
    return JsonResponse({'status': 'stopped'})

@api_view(['GET'])
def mqtt_publisher_status(request):
    return JsonResponse({'running': get_publisher_status() == 'running'})

@api_view(['POST'])
def start_subscriber(request):
    global subscriber_instance

    if subscriber_instance is None or not subscriber_instance.connected:
        def run():
            global subscriber_instance
            subscriber_instance = MQTTSubscriber()
            subscriber_instance.start()
            while True:
                time.sleep(1)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return JsonResponse({'status': 'started'})
    else:
        return JsonResponse({'status': 'already running'})

@api_view(['POST'])
def stop_subscriber(request):
    global subscriber_instance

    if subscriber_instance and subscriber_instance.connected:
        subscriber_instance.stop()
        subscriber_instance = None
        return JsonResponse({'status': 'stopped'})
    return JsonResponse({'status': 'already stopped'})

@api_view(['GET'])
def subscriber_status(request):
    running = subscriber_instance is not None and subscriber_instance.connected
    return JsonResponse({'running': running})