from django.urls import path
from .views import (start_mqtt_publisher, stop_mqtt_publisher, mqtt_publisher_status, start_subscriber, stop_subscriber,
                    subscriber_status)


# Urls for endpoints of MQTT clients
urlpatterns = [
    # Starting publisher
    path('publisher/start/', start_mqtt_publisher, name='mqtt-publisher-start'),
    # Stopping publisher
    path('publisher/stop/', stop_mqtt_publisher, name='mqtt-publisher-stop'),
    # Getting publisher status
    path('publisher/status/', mqtt_publisher_status, name='mqtt-publisher-status'),
    # Starting subscriber
    path('subscriber/start/', start_subscriber),
    # Stopping subscriber
    path('subscriber/stop/', stop_subscriber),
    # Getting subscriber status
    path('subscriber/status/', subscriber_status),
]