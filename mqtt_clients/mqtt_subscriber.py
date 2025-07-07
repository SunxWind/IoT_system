import os
import sys
import time
import ssl
import logging
import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,  # Use DEBUG for detailed output, WARNING for general info
    format="%(asctime)s [%(levelname)s] %(message)s",
)


class MQTTSubscriber:
    def __init__(self):
        """
        Initialize the MQTTSubscriber instance.
        Sets up Django, loads MQTTDevice model, and attempts to initialize the MQTT client.
        """
        self.setup_django()
        from mqtt_devices.models import MQTTDevice
        self.Device = MQTTDevice
        self.client = None
        self.connected = False
        self.max_retries = 5
        self.retry_delay = 3

        self.setup_django()  # Redundant but safe in case the first fails silently

        try:
            self.initialize_client()
        except Exception as e:
            logger.error(f"Initial MQTT connection failed: {e}")

    def setup_django(self):
        """
        Set up Django settings so models can be imported and used.
        Appends parent directory to sys.path and configures environment variables for Django.
        """
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "IoT_system.settings")
        import django
        django.setup()

    def initialize_client(self):
        """
        Initialize the MQTT client, set up callbacks, and attempt connection with retries.
        Raises:
            Exception if connection fails after all retries or configuration is invalid.
        """
        try:
            broker = os.getenv('MQTT_BROKER')
            port = int(os.getenv('MQTT_PORT'))
            username = os.getenv('MQTT_USERNAME')
            password = os.getenv('MQTT_PASSWORD')

            if not broker:
                raise ValueError("MQTT_BROKER environment variable not set")

            # Create and configure MQTT client
            self.client = mqtt.Client(
                client_id="device_123_subscriber",
                callback_api_version=CallbackAPIVersion.VERSION2,
                transport="tcp"
            )
            self.client.tls_set(
                ca_certs="/etc/mosquitto/certs/ca.crt",
                certfile="/etc/mosquitto/certs/clients/client.crt",
                keyfile="/etc/mosquitto/certs/clients/client.key",
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLS_CLIENT)
            self.client.username_pw_set(username, password)

            # Socket event logging for advanced debugging
            self.client.on_socket_open = lambda client, userdata, sock: logger.info("Socket opened")
            self.client.on_socket_close = lambda client, userdata, sock: logger.warning("Socket closed")
            self.client.on_socket_register_write = lambda client, userdata, sock: logger.debug("Socket write registered")
            self.client.on_socket_unregister_write = lambda client, userdata, sock: logger.debug("Socket write unregistered")

            # Assign callbacks
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.on_disconnect = self.on_disconnect

            # Retry loop for connecting to MQTT broker
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
        """
        Check basic network connectivity to the MQTT broker using TCP socket.
        Returns:
            bool: True if connection is successful, False otherwise.
        """
        import socket
        broker = os.getenv('MQTT_BROKER')
        port = int(os.getenv('MQTT_PORT', 8883))

        try:
            with socket.create_connection((broker, port), timeout=5):
                return True
        except socket.error as e:
            logger.error(f"Network connectivity check failed: {e}")
            return False

    def on_connect(self, client, userdata, flags, rc, properties=None):
        """
        Callback when the client connects to the broker.
        Subscribes to device topics on successful connection.
        """
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
        """
        Callback for handling incoming MQTT messages.

        Handles commands for devices based on the topic:
        Expected format: mqtt_devices/<serial_number>/command

        Valid commands:
            - START: Sets device as active
            - STOP: Sets device as inactive
        """
        try:
            topic = msg.topic
            payload = msg.payload.decode()
            logger.info(f"Received message on topic {topic}: {payload}")

            # Validate topic structure
            parts = topic.split('/')
            if len(parts) != 3 or parts[0] != "mqtt_devices" or parts[2] != "command":
                logger.warning(f"Invalid topic format: {topic}")
                return

            serial_number = parts[1]

            # Fetch device by serial number
            try:
                device = self.Device.objects.get(serial_number=serial_number)
            except self.Device.DoesNotExist:
                logger.error(f"Device with serial_number {serial_number} not found.")
                client.publish(f"devices/{serial_number}/error", "Device not found")
                return

            # Handle commands
            if payload.upper() == "START":
                device.is_active = True
                device.save(update_fields=["is_active"])
                logger.info(f"Device {serial_number} set to active")
            elif payload.upper() == "STOP":
                device.is_active = False
                device.save(update_fields=["is_active"])
                logger.info(f"Device {serial_number} set to inactive")
            else:
                logger.warning(f"Unknown command '{payload}' for device {serial_number}")
                client.publish(f"devices/{serial_number}/error", f"Unknown command: {payload}")

        except Exception as e:
            logger.exception("Error processing MQTT message")
            try:
                client.publish(f"devices/{serial_number}/error", str(e))
            except:
                pass  # Prevent crash if publishing error fails

    def on_disconnect(self, client, userdata, flags, rc, properties=None):
        """
        Callback triggered when client disconnects from the broker.
        If disconnection was unexpected, attempts reconnection.
        """
        self.connected = False
        logger.warning(f"Disconnected from MQTT broker (code: {rc})")
        if rc != 0:  # Unexpected disconnect
            logger.info("Attempting to reconnect...")
            time.sleep(5)
            self.initialize_client()

    def subscribe_to_devices(self):
        """
        Subscribe to MQTT topics for all active devices stored in the database.

        Returns:
            bool: True if all subscriptions were successful, False otherwise.
        """
        logger.info("Attempting to subscribe to device topics")

        if not self.connected:
            logger.error("Cannot subscribe - not connected to broker")
            return False

        try:
            dev_objects = self.Device.objects.filter(is_active=True)
            logger.info(f"Found {dev_objects.count} active devices")

            # Subscribe to each device's topic
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
        """
        Start the MQTT client if not already connected.
        """
        if not self.connected:
            self.initialize_client()

    def stop(self):
        """
        Stop and clean up the MQTT client.
        Disconnects from the broker and stops the loop.
        """
        if self.client:
            if self.connected:
                self.client.disconnect()
            self.client.loop_stop()
            self.client = None  # Ensure cleanup
        logger.info("MQTT client stopped")


if __name__ == "__main__":
    # Entry point when running the module directly
    subscriber = MQTTSubscriber()
    subscriber.validate_connection()

    try:
        while True:
            time.sleep(1)  # Keep the main thread alive
    except KeyboardInterrupt:
        print("Exiting...")
        subscriber.stop()
