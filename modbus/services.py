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


# Configure logging
log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for more detailed output
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# Dictionary to store references to running client threads
client_threads = {}

# Load environment variables
load_dotenv()
MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB = os.getenv('MONGO_DB_NAME')
MONGO_COLLECTION = os.getenv('MODBUS_COLLECTION_NAME')

# Initialize MongoDB client and target collection
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB]
collection = db[MONGO_COLLECTION]


def modbus_client_worker(device_id):
    """
    Worker thread function that continuously reads data from a Modbus device
    and logs it into MongoDB until the device is deactivated.

    Args:
        device_id (int): The primary key of the ModbusDevice instance.
    """
    try:
        device = ModbusDevice.objects.get(pk=device_id)
    except ModbusDevice.DoesNotExist:
        log.error(f"Device {device_id} does not exist.")
        return

    # Create a Modbus TCP client for the specified device
    client = ModbusTcpClient(device.host, port=device.port, timeout=15)

    if not client.connect():
        log.error(f"Cannot connect to Modbus device {device.name} at {device.host}:{device.port}")
        device.is_running = False
        device.save()
        return

    log.info(f"Started Modbus client for device {device.name}")
    try:
        while True:
            # Refresh the device instance to check if it's still active
            device.refresh_from_db()
            if not device.is_active:
                log.info(f"Device {device.name} is not active. Stopping client.")
                break

            # Read two 16-bit registers (32-bit float) from the device
            rr = client.read_holding_registers(device.register_address, count=2, slave=device.slave_id)
            if rr.isError():
                log.warning(f"Failed to read registers for device {device.name}")
            else:
                # Decode the 32-bit float from the register values
                decoder = BinaryPayloadDecoder.fromRegisters(rr.registers, byteorder=Endian.BIG)
                value = decoder.decode_32bit_float()

                # Save the value to MongoDB with timestamp and device info
                record = {
                    "device_id": device.pk,
                    "device_name": device.name,
                    "timestamp": time.time(),
                    "value": value,
                }
                collection.insert_one(record)
                log.info(f"Logged value {value} for device {device.name} in MongoDB")

            # Wait 5 seconds before the next reading
            time.sleep(5)

    except Exception as e:
        log.exception(f"Unhandled exception in client thread for device {device.name}: {e}")

    finally:
        # Ensure proper cleanup on exit
        client.close()
        device.is_running = False
        device.save()
        log.info(f"Stopped Modbus client for device {device.name}")

    # This redundant block ensures cleanup in any case (safe fallback)
    client.close()
    device.is_running = False
    device.save()
    log.info(f"Stopped Modbus client for device {device.name}")


def start_client(device: ModbusDevice):
    """
    Starts a new Modbus client thread for the given device, if it's not already running.

    Args:
        device (ModbusDevice): The Modbus device to start a client for.
    """
    if device.pk in client_threads and client_threads[device.pk].is_alive():
        log.warning(f"Client for device {device.name} is already running.")
        return

    # Mark the device as running in the database
    device.is_running = True
    device.save()

    # Create and start a background thread to handle the device's communication
    thread = threading.Thread(target=modbus_client_worker, args=(device.pk,), daemon=True)
    thread.start()
    client_threads[device.pk] = thread
    log.info(f"Started client thread for device {device.name}")


def stop_client(device: ModbusDevice):
    """
    Signals the Modbus client thread to stop by deactivating the device.

    Args:
        device (ModbusDevice): The Modbus device whose client should be stopped.
    """
    device.is_running = False
    device.save()
    log.info(f"Set is_active=False for device {device.name}, client will stop shortly.")
