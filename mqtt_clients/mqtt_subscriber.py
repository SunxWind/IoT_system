import os
import sys
import time
import logging
import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,  # or DEBUG for more detail
    format="%(asctime)s [%(levelname)s] %(message)s",
)

class MQTTSubscriber:
    def __init__(self):
        self.setup_django()
        from mqtt_devices.models import MQTTDevice
        self.Device = MQTTDevice
        self.client = None
        self.connected = False
        self.max_retries = 5
        self.retry_delay = 3

        self.setup_django()

        try:
            self.initialize_client()
        except Exception as e:
            logger.error(f"Initial MQTT connection failed: {e}")

    def setup_django(self):
        """Set up Django settings once"""
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "IoT_system.settings")
        import django
        django.setup()

    def initialize_client(self):
        """Initialize MQTT client with connection retries"""
        try:
            broker = os.getenv('MQTT_BROKER')
            port = int(os.getenv('MQTT_PORT'))

            if not broker:
                raise ValueError("MQTT_BROKER environment variable not set")

            self.client = mqtt.Client(
                client_id=f"django-sub-{time.time_ns()}",
                callback_api_version=CallbackAPIVersion.VERSION2,
                transport="tcp"
            )

            self.client.on_socket_open = lambda client, userdata, sock: logger.info("Socket opened")
            self.client.on_socket_close = lambda client, userdata, sock: logger.warning("Socket closed")
            self.client.on_socket_register_write = lambda client, userdata, sock: logger.debug(
                "Socket write registered")
            self.client.on_socket_unregister_write = lambda client, userdata, sock: logger.debug(
                "Socket write unregistered")

            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.on_disconnect = self.on_disconnect


            for attempt in range(1, self.max_retries + 1):
                try:
                    self.client.connect(broker, port, 60)
                    self.client.loop_start()
                    logger.info(f"Connecting to MQTT broker (attempt {attempt})...")
                    time.sleep(2 if attempt == 1 else 1)
                    if self.connected:
                        return
                except Exception as e:
                    logger.warning(f"Connection attempt {attempt} failed: {e}")
                    if attempt < self.max_retries:
                        time.sleep(self.retry_delay * attempt)

            raise ConnectionError(f"Failed to connect after {self.max_retries} attempts")

        except KeyError as e:
            logger.error(f"Missing environment variable: {e}")
            raise
        except Exception as e:
            logger.error(f"MQTT initialization failed: {e}")
            raise

    def validate_connection(self):
        """Verify we can reach the broker"""
        import socket
        broker = os.getenv('MQTT_BROKER')
        port = int(os.getenv('MQTT_PORT', 1883))

        try:
            with socket.create_connection((broker, port), timeout=5):
                return True
        except socket.error as e:
            logger.error(f"Network connectivity check failed: {e}")
            return False

    def on_connect(self, client, userdata, flags, rc, properties=None):
        print(f"on_connect called with rc={rc}")
        if rc == 0:
            self.connected = True
            logger.info("Successfully connected to MQTT broker")
            try:
                self.subscribe_to_devices()
            except Exception as e:
                logger.error(f"Subscription failed in on_connect: {e}")
        else:
            logger.error(f"Connection failed with code {rc}")

    def on_message(self, client, userdata, msg):

        logger.info(f"Received message on topic {msg.topic}: {msg.payload.decode()}")
        topic = msg.topic
        payload = msg.payload.decode()
        serial_number = topic.split('/')[1]  # Extract from topic
        try:
            device = self.Device.objects.get(serial_number=serial_number)
            if payload == "START":
                device.is_active = True
                device.save()
            elif payload == "STOP":
                device.is_active = False
                device.save()
            elif payload == "RESET":
                # Trigger Modbus reset (example)
                client.write_register(address=0, value=1, slave=device.slave_id)
            elif payload == "PAUSE":
                # Custom logic (e.g., set a 'paused' flag in DB)
                device.is_paused = True
            device.save()
        except Exception as e:
            client.publish(f"devices/{serial_number}/error", str(e))

    def on_disconnect(self, client, userdata, flags, rc, properties=None):
        self.connected = False
        logger.warning(f"Disconnected from MQTT broker (code: {rc})")
        if rc != 0:  # Only attempt reconnect if unexpected disconnect
            logger.info("Attempting to reconnect...")
            time.sleep(5)
            self.initialize_client()

    def subscribe_to_devices(self):
        """Subscribe to active device topics"""
        logger.info("Attempting to subscribe to device topics")

        if not self.connected:
            logger.error("Cannot subscribe - not connected to broker")
            return False

        try:
            dev_objects = self.Device.objects.filter(is_active=True)
            logger.info(f"Found {dev_objects.count()} active devices")

            for device in dev_objects:
                result, mid = self.client.subscribe(device.mqtt_command_topic)
                if result == mqtt.MQTT_ERR_SUCCESS:
                    logger.info(f"Successfully subscribed to {device.mqtt_command_topic}")
                else:
                    logger.warning(f"Failed to subscribe to {device.mqtt_command_topic}, error code: {result}")

            logger.info("Subscribed to all active device topics")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe: {e}")
            return False

    def start(self):
        """Start the MQTT client"""
        if not self.connected:
            self.initialize_client()

    def stop(self):
        """Stop the MQTT client"""
        if self.client:
            if self.connected:
                self.client.disconnect()
            self.client.loop_stop()
            self.client = None  # Important for cleanup
        logger.info("MQTT client stopped")


if __name__ == "__main__":
    subscriber = MQTTSubscriber()
    subscriber.validate_connection()

    try:
        while True:
            time.sleep(1)  # Keep main thread alive
    except KeyboardInterrupt:
        print("Exiting...")
        subscriber.stop()

