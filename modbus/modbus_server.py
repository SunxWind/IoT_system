import os
import asyncio
import threading
import logging
from dotenv import load_dotenv
from pymodbus.datastore import ModbusServerContext, ModbusSlaveContext, ModbusSequentialDataBlock
from pymodbus.payload import BinaryPayloadBuilder
from pymodbus.constants import Endian
from pymodbus.server import StartAsyncTcpServer
import aiohttp

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
log = logging.getLogger("modbus")

load_dotenv()

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
API_URL = "https://api.polygon.io/v3/reference/dividends"
MODBUS_SERVER_HOST = os.getenv("MODBUS_SERVER_IP", "127.0.0.1")
MODBUS_SERVER_PORT = int(os.getenv("MODBUS_SERVER_PORT", 5020))

server_should_run = False
server_task = None
server_thread = None
server_loop = None

# Shared context for Modbus registers
store = ModbusSlaveContext(hr=ModbusSequentialDataBlock(0, [0]*100))
context = ModbusServerContext(slaves=store, single=True)

async def fetch_polygon_price():
    try:
        headers = {"Authorization": f"Bearer {POLYGON_API_KEY}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers, timeout=10) as response:
                response.raise_for_status()
                data = await response.json()
                return data["results"][0]["cash_amount"]
    except Exception as e:
        log.error(f"Polygon API error: {e}")
        return None

async def updating_loop():
    """Periodically fetch price and update Modbus registers while server_should_run is True"""
    while server_should_run:
        value = await fetch_polygon_price()
        if value is not None:
            builder = BinaryPayloadBuilder(byteorder=Endian.BIG)
            builder.add_32bit_float(value)
            payload = builder.to_registers()
            context[0x00].setValues(3, 0, payload)  # Function code 3 = Holding Registers, start address 0
            log.info(f"Updated Modbus register with value: {value}")
        await asyncio.sleep(10)

async def modbus_server_loop():
    """Main async server task: run server and updating loop concurrently"""
    server = StartAsyncTcpServer(context, address=(MODBUS_SERVER_HOST, MODBUS_SERVER_PORT))
    log.info(f"Modbus server starting on {MODBUS_SERVER_HOST}:{MODBUS_SERVER_PORT}")

    # Run server and updating loop concurrently; server() never ends until cancelled
    await asyncio.gather(
        server,
        updating_loop(),
    )


def run_server_loop():
    global server_should_run, server_task, server_loop

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    server_loop = loop  # Save loop globally
    server_should_run = True
    try:
        server_task = loop.create_task(modbus_server_loop())
        loop.run_until_complete(server_task)
    except asyncio.CancelledError:
        log.info("Modbus server task cancelled")
    finally:
        server_should_run = False
        loop.close()
        log.info("Modbus server stopped")

def start_server():
    global server_thread, server_should_run

    if server_thread and server_thread.is_alive():
        log.warning("Server already running")
        return

    server_thread = threading.Thread(target=run_server_loop, daemon=True)
    server_thread.start()
    log.info("Server start command issued")

def stop_server():
    global server_should_run, server_task, server_loop

    if not server_should_run:
        log.warning("Server is not running")
        return

    server_should_run = False

    if server_loop and server_task:
        # Schedule cancellation on the server's event loop thread
        server_loop.call_soon_threadsafe(server_task.cancel)

    if server_thread:
        server_thread.join(timeout=5)
    log.info("Server stop command issued")

def is_server_running():
    return server_thread is not None and server_thread.is_alive()
