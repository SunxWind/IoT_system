import os
from dotenv import load_dotenv
import time
import ssl
import threading
import json
import requests
import paho.mqtt.client as mqtt
from pymongo import MongoClient

# Load environment variables from .env file
load_dotenv()

# Configuration parameters from .env
BROKER_ADDRESS = os.getenv('MQTT_BROKER')
BROKER_PORT = int(os.getenv('MQTT_PORT'))
MQTT_USERNAME = os.getenv('MQTT_USERNAME')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD')
PUBLISH_TOPIC = os.getenv('MQTT_PUBLISH_TOPIC')
INTERVAL = 10  # Interval between publishing in seconds

MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = os.getenv('MONGO_DB_NAME')
COLLECTION_NAME = os.getenv('MQTT_COLLECTION_NAME')

API_KEY = os.getenv('COINCAP_API_KEY')
API_URL = "https://rest.coincap.io/v3/assets"

# Initialize MongoDB client once at module level
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
collection = db[COLLECTION_NAME]

# Internal thread control flags
_publisher_thread = None
_stop_event = threading.Event()
_is_running = False


def fetch_crypto_data(limit=2):
    """
    Fetch cryptocurrency data from CoinCap API.

    Args:
        limit (int): Number of top assets to retrieve.

    Returns:
        list: List of dictionaries containing name, symbol, price in USD, and timestamp.
    """
    headers = {"Authorization": f"Bearer {API_KEY}"}
    try:
        response = requests.get(API_URL, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()["data"]
        selected = data[:limit]  # Limit the number of returned assets

        result = []
        for asset in selected:
            print(asset)  # Debug print of raw API data
            result.append({
                "name": asset["name"],
                "symbol": asset["symbol"],
                "priceUsd": round(float(asset["priceUsd"]), 2),
                "timestamp": time.time()
            })
        return result
    except Exception as e:
        print(f"[ERROR] Failed to fetch crypto data: {e}")
        return []


def _run_publisher():
    """
    Internal thread function to continuously publish crypto data via MQTT
    and store it into MongoDB every INTERVAL seconds.
    """
    # Set up MQTT client with TLS encryption and authentication
    client = mqtt.Client(client_id="device_123_publisher")
    client.tls_set(
        ca_certs="/etc/mosquitto/certs/ca.crt",
        certfile="/etc/mosquitto/certs/clients/client.crt",
        keyfile="/etc/mosquitto/certs/clients/client.key",
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLS_CLIENT)
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.connect(BROKER_ADDRESS, BROKER_PORT, 60)
    client.loop_start()

    # Main publishing loop
    while not _stop_event.is_set():
        data = fetch_crypto_data()
        if data:
            payload = json.dumps(data)
            client.publish(PUBLISH_TOPIC, payload)

            # Save each item to MongoDB
            for item in data:
                collection.insert_one(item)

        time.sleep(INTERVAL)

    # Clean shutdown
    client.loop_stop()
    client.disconnect()


def on_connect(client, userdata, flags, rc):
    """
    MQTT on_connect callback function to report connection result.

    Args:
        client: The client instance for this callback.
        userdata: The private user data.
        flags: Response flags from the broker.
        rc: The connection result code.
    """
    if rc == 0:
        print("[INFO] Connected to MQTT broker")
    else:
        print(f"[ERROR] Failed to connect. Return code: {rc}")


def publish_loop(client):
    """
    Alternative loop for testing or custom publishing logic. Fetches and publishes
    crypto data indefinitely.

    Args:
        client: MQTT client instance used to publish messages.
    """
    while True:
        crypto_data = fetch_crypto_data()
        if crypto_data:
            payload = json.dumps(crypto_data)
            client.publish(PUBLISH_TOPIC, payload)
            print(f"[PUBLISHED] {payload}")

            # Insert each item into MongoDB
            for item in crypto_data:
                try:
                    collection.insert_one(item)
                    print(f"[MONGODB] Inserted: {item}")
                except Exception as e:
                    print(f"[ERROR] MongoDB insert failed: {e}")
        else:
            print("[INFO] No crypto data fetched.")

        time.sleep(INTERVAL)


def start_publisher():
    """
    Starts the publisher thread if it is not already running.

    Returns:
        bool: True if started successfully, False if already running.
    """
    global _publisher_thread, _is_running
    if _publisher_thread and _publisher_thread.is_alive():
        return False

    _stop_event.clear()
    _publisher_thread = threading.Thread(target=_run_publisher, daemon=True)
    _publisher_thread.start()
    _is_running = True
    return True


def stop_publisher():
    """
    Signals the publisher thread to stop and updates internal running state.

    Returns:
        bool: Always returns True.
    """
    global _is_running
    _stop_event.set()
    _is_running = False
    return True


def get_publisher_status():
    """
    Returns the current status of the publisher.

    Returns:
        str: 'running' if active, 'stopped' otherwise.
    """
    return "running" if _is_running else "stopped"
