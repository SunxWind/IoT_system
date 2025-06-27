import os
import threading
import time
import logging
from dotenv import load_dotenv
from pymodbus.client import ModbusTcpClient
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian
from pymongo import MongoClient
from .models import ModbusDevice


# Configuration
log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,  # or DEBUG for more detail
    format="%(asctime)s [%(levelname)s] %(message)s",
)
client_threads = {}

load_dotenv()
MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB = os.getenv('MONGO_DB_NAME')
MONGO_COLLECTION = os.getenv('MODBUS_COLLECTION_NAME')

mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB]
collection = db[MONGO_COLLECTION]


def modbus_client_worker(device_id):
    try:
        device = ModbusDevice.objects.get(pk=device_id)
    except ModbusDevice.DoesNotExist:
        log.error(f"Device {device_id} does not exist.")
        return

    client = ModbusTcpClient(device.host, port=device.port, timeout=15)

    if not client.connect():
        log.error(f"Cannot connect to Modbus device {device.name} at {device.host}:{device.port}")
        device.is_running = False
        device.save()
        return

    log.info(f"Started Modbus client for device {device.name}")
    try:
        while True:
            device.refresh_from_db()
            if not device.is_active:
                log.info(f"Device {device.name} is not active. Stopping client.")
                break

            rr = client.read_holding_registers(device.register_address, count=2, slave=device.slave_id)
            if rr.isError():
                log.warning(f"Failed to read registers for device {device.name}")
            else:
                decoder = BinaryPayloadDecoder.fromRegisters(rr.registers, byteorder=Endian.BIG)
                value = decoder.decode_32bit_float()

                # Uložit do MongoDB s časovým razítkem a ID zařízení
                record = {
                    "device_id": device.pk,
                    "device_name": device.name,
                    "timestamp": time.time(),
                    "value": value,
                }
                collection.insert_one(record)
                log.info(f"Logged value {value} for device {device.name} in MongoDB")

            time.sleep(5)
    except Exception as e:
        log.exception(f"Unhandled exception in client thread for device {device.name}: {e}")
    finally:
        client.close()
        device.is_running = False
        device.save()
        log.info(f"Stopped Modbus client for device {device.name}")

    client.close()
    device.is_running = False
    device.save()
    log.info(f"Stopped Modbus client for device {device.name}")


def start_client(device: ModbusDevice):
    if device.pk in client_threads and client_threads[device.pk].is_alive():
        log.warning(f"Client for device {device.name} is already running.")
        return

    device.is_running = True
    device.save()

    thread = threading.Thread(target=modbus_client_worker, args=(device.pk,), daemon=True)
    thread.start()
    client_threads[device.pk] = thread
    log.info(f"Started client thread for device {device.name}")


def stop_client(device: ModbusDevice):
    device.is_running = False
    device.save()
    log.info(f"Set is_active=False for device {device.name}, client will stop shortly.")
