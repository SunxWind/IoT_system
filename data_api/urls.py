from django.urls import path
from .views import MQTTDataMongoView, SendMQTTCommand


# Urls for main MQTT endpoints
urlpatterns = [
    # Visualization of sensor data collected in MongoDB
    path('mqtt-data/', MQTTDataMongoView.as_view(), name='mqtt-data'),
    # Sending control commands to MQTT devices
    path('mqtt-control/', SendMQTTCommand.as_view(), name='mqtt-control'),
]
