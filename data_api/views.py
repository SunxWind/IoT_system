import os
import logging
import ssl
from pymongo import MongoClient
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from dotenv import load_dotenv
import paho.mqtt.publish as publish
from mqtt_devices.models import MQTTDevice

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = os.getenv('MONGO_DB_NAME')
MQTT_COLLECTION_NAME = os.getenv('MQTT_COLLECTION_NAME')
BROKER = os.getenv('MQTT_BROKER')
PORT = int(os.getenv('MQTT_PORT'))
USERNAME = os.getenv('MQTT_USERNAME')
PASSWORD = os.getenv('MQTT_PASSWORD')

logger = logging.getLogger(__name__)

class MQTTDataMongoView(APIView):
    """APIView for retrieving mqtt data stored in MongoDB."""
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:

            mongo_client = MongoClient(MONGO_URI)
            db = mongo_client[DB_NAME]
            collection = db[MQTT_COLLECTION_NAME]
            data_cursor = collection.find().sort("timestamp", -1).limit(20)
            result = []
            for item in data_cursor:
                print(item)
                result.append({
                    "timestamp": item.get("timestamp"),
                    "name": item.get("name"),
                    "symbol": item.get("symbol"),
                    "priceUsd": item.get("priceUsd")
                })
            return Response(result)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SendMQTTCommand(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serial_number = request.data.get("serial_number")
        command = request.data.get("command")
        qos = request.data.get("qos", 0)  # Default QoS=0

        logger.info(f"The command {command} was sent to device-{serial_number}")

        if not serial_number or not command:
            logger.warning(f"Missing parameters. Serial: {serial_number}, Command: {command}")
            return Response(
                {"error": "Both 'serial_number' and 'command' are required."},
                status=400
            )

        try:
            device = MQTTDevice.objects.get(serial_number=serial_number)
            logger.info(f"Device-{device} was found")
        except MQTTDevice.DoesNotExist:
            logger.warning(f"Device not found or inactive: {serial_number}")
            return Response(
                {"error": "Device not found or inactive."},
                status=404
            )

        # Use the device's topic if available, otherwise fall back to default pattern
        topic = device.mqtt_command_topic or f"devices/{device.serial_number}/command"
        print(topic, command)
        try:
            publish.single(
                topic,
                payload=command,
                qos=qos,
                hostname=BROKER,
                port=PORT,
                auth={
                    'username': USERNAME,
                    'password': PASSWORD
                },
                tls={
                    'ca_certs': '/etc/mosquitto/certs/ca.crt',
                    'certfile': '/etc/mosquitto/certs/clients/client.crt',
                    'keyfile': '/etc/mosquitto/certs/clients/client.key',
                    'cert_reqs': ssl.CERT_REQUIRED,
                    'tls_version': ssl.PROTOCOL_TLS_CLIENT,
                },
                client_id=f"publisher_{serial_number}"
            )
            logger.info(f"Sent command to {topic}: {command}")
            return Response({
                "status": "success",
                "device": device.name,
                "serial_number": device.serial_number,
                "command": command,
                "mqtt_topic": topic,
                "qos": qos
            })
        except Exception as e:
            logger.error(f"MQTT publish failed: {str(e)}")
            return Response(
                {"error": "Failed to send MQTT command. Please try again."},
                status=500
            )