from django.urls import path
from .views import (start_mqtt_publisher, stop_mqtt_publisher, mqtt_publisher_status, start_subscriber, stop_subscriber,
                    subscriber_status)

urlpatterns = [
    path('publisher/start/', start_mqtt_publisher, name='mqtt-publisher-start'),
    path('publisher/stop/', stop_mqtt_publisher, name='mqtt-publisher-stop'),
    path('publisher/status/', mqtt_publisher_status, name='mqtt-publisher-status'),
    path('subscriber/start/', start_subscriber),
    path('subscriber/stop/', stop_subscriber),
    path('subscriber/status/', subscriber_status),
]