from django.urls import path
from .views import MQTTDataMongoView, SendMQTTCommand

urlpatterns = [
    path('mqtt-data/', MQTTDataMongoView.as_view(), name='mqtt-data'),
    path('mqtt-control/', SendMQTTCommand.as_view(), name='mqtt-control'),
]
