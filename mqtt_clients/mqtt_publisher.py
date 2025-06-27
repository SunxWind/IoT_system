import os
from dotenv import load_dotenv
import time
import threading
import json
import requests
import paho.mqtt.client as mqtt
from pymongo import MongoClient

load_dotenv()

# Configuration
BROKER_ADDRESS = os.getenv('MQTT_BROKER')
BROKER_PORT = int(os.getenv('MQTT_PORT'))
PUBLISH_TOPIC = "sensors/crypto"
INTERVAL = 10  # seconds

MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = os.getenv('MONGO_DB_NAME')
COLLECTION_NAME = os.getenv('MQTT_COLLECTION_NAME')

API_KEY = os.getenv('COINCAP_API_KEY')
API_URL = "https://rest.coincap.io/v3/assets"

# Initialize MongoDB client once
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
collection = db[COLLECTION_NAME]

_publisher_thread = None
_stop_event = threading.Event()
_is_running = False

def fetch_crypto_data(limit=2):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    try:
        response = requests.get(API_URL, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()["data"]
        selected = data[:limit]

        result = []
        for asset in selected:
            print(asset)  # debug print
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
    client = mqtt.Client()
    client.connect(BROKER_ADDRESS, BROKER_PORT, 60)
    client.loop_start()

    while not _stop_event.is_set():
        data = fetch_crypto_data()
        if data:
            payload = json.dumps(data)
            client.publish(PUBLISH_TOPIC, payload)
            for item in data:
                collection.insert_one(item)
        time.sleep(INTERVAL)

    client.loop_stop()
    client.disconnect()


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[INFO] Connected to MQTT broker")
    else:
        print(f"[ERROR] Failed to connect. Return code: {rc}")

def publish_loop(client):
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
    global _publisher_thread, _is_running
    if _publisher_thread and _publisher_thread.is_alive():
        return False
    _stop_event.clear()
    _publisher_thread = threading.Thread(target=_run_publisher, daemon=True)
    _publisher_thread.start()
    _is_running = True
    return True

def stop_publisher():
    global _is_running
    _stop_event.set()
    _is_running = False
    return True

def get_publisher_status():
    return "running" if _is_running else "stopped"