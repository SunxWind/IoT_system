import time
import threading
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated

from .mqtt_publisher import start_publisher, stop_publisher, get_publisher_status
from .mqtt_subscriber import MQTTSubscriber


# Global instance of the MQTT subscriber
subscriber_instance = None


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_mqtt_publisher(request):
    """
    Starts the MQTT publisher if it's not already running.

    Returns:
        JsonResponse: JSON indicating whether the publisher was started or already running.
    """
    started = start_publisher()
    return JsonResponse({'status': 'started' if started else 'already_running'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def stop_mqtt_publisher(request):
    """
    Stops the MQTT publisher.

    Returns:
        JsonResponse: JSON indicating that the publisher was stopped.
    """
    stop_publisher()
    return JsonResponse({'status': 'stopped'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mqtt_publisher_status(request):
    """
    Returns the current status of the MQTT publisher.

    Returns:
        JsonResponse: JSON with key 'running' indicating if the publisher is currently active.
    """
    return JsonResponse({'running': get_publisher_status() == 'running'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_subscriber(request):
    """
    Starts the MQTT subscriber in a background thread if it is not already running.

    Returns:
        JsonResponse: JSON indicating whether the subscriber was started or already running.
    """
    global subscriber_instance

    # Start a new subscriber if none exists or it's not connected
    if subscriber_instance is None or not subscriber_instance.connected:
        def run():
            """
            Runs the MQTT subscriber in an infinite loop in a background thread.
            """
            global subscriber_instance
            subscriber_instance = MQTTSubscriber()
            subscriber_instance.start()
            # Keep the thread alive to ensure MQTT loop stays active
            while True:
                time.sleep(1)

        # Start the subscriber in a daemon thread
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return JsonResponse({'status': 'started'})
    else:
        return JsonResponse({'status': 'already running'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def stop_subscriber(request):
    """
    Stops the running MQTT subscriber if it is active.

    Returns:
        JsonResponse: JSON indicating whether the subscriber was stopped or was already stopped.
    """
    global subscriber_instance

    if subscriber_instance and subscriber_instance.connected:
        subscriber_instance.stop()
        subscriber_instance = None
        return JsonResponse({'status': 'stopped'})
    return JsonResponse({'status': 'already stopped'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def subscriber_status(request):
    """
    Returns the current running status of the MQTT subscriber.

    Returns:
        JsonResponse: JSON with key 'running' indicating if the subscriber is active.
    """
    running = subscriber_instance is not None and subscriber_instance.connected
    return JsonResponse({'running': running})
