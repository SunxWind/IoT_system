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


# Configure logging format and level
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
log = logging.getLogger("modbus")

# Load environment variables from .env file
load_dotenv()

# Load Polygon API key and default server configuration from environment
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
API_URL = "https://api.polygon.io/v3/reference/dividends"  # Polygon API endpoint for dividend data
MODBUS_SERVER_HOST = os.getenv("MODBUS_SERVER_IP", "127.0.0.1")  # Default to localhost if not set
MODBUS_SERVER_PORT = int(os.getenv("MODBUS_SERVER_PORT", 15020))  # Default port is 15020

# Global flags and references to control server lifecycle
server_should_run = False  # Flag to control the update loop
server_task = None  # Reference to the async Modbus server task
server_thread = None  # Reference to the background thread running the server
server_loop = None  # Reference to the asyncio event loop used by the server

# Initialize Modbus register context with 100 holding registers, all set to 0
store = ModbusSlaveContext(hr=ModbusSequentialDataBlock(0, [0] * 100))
context = ModbusServerContext(slaves=store, single=True)  # Single slave device mode


async def fetch_polygon_price():
    """
    Fetch the latest dividend cash_amount value from Polygon API.

    Returns:
        float or None: The latest cash_amount value if successful, or None on error.
    """
    try:
        headers = {"Authorization": f"Bearer {POLYGON_API_KEY}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers, timeout=10) as response:
                response.raise_for_status()  # Raise exception for 4xx/5xx responses
                data = await response.json()
                return data["results"][0]["cash_amount"]  # Return first result's cash_amount
    except Exception as e:
        log.error(f"Polygon API error: {e}")
        return None


async def updating_loop():
    """
    Periodically fetch price from Polygon and update Modbus holding registers.
    Continues running as long as `server_should_run` is True.
    """
    while server_should_run:
        value = await fetch_polygon_price()
        if value is not None:
            # Build 32-bit float payload in BIG endian byte order
            builder = BinaryPayloadBuilder(byteorder=Endian.BIG)
            builder.add_32bit_float(value)
            payload = builder.to_registers()

            # Update holding registers (function code 3) at address 0
            context[0x00].setValues(3, 0, payload)
            log.info(f"Updated Modbus register with value: {value}")
        else:
            log.warning("No value fetched; registers not updated")

        # Wait before fetching again
        await asyncio.sleep(10)


async def modbus_server_loop():
    """
    Coroutine that starts the Modbus TCP server and the updating loop concurrently.
    This will run until cancelled.
    """
    # Start Modbus server on specified host and port
    server = StartAsyncTcpServer(context, address=(MODBUS_SERVER_HOST, MODBUS_SERVER_PORT))
    log.info(f"Modbus server starting on {MODBUS_SERVER_HOST}:{MODBUS_SERVER_PORT}")

    # Run both the TCP server and register updating loop at the same time
    await asyncio.gather(
        server,
        updating_loop(),
    )


def run_server_loop():
    """
    Create a new asyncio event loop in a background thread and start the Modbus server.
    This function is blocking and runs until the server is stopped.
    """
    global server_should_run, server_task, server_loop

    # Create and set a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    server_loop = loop  # Save the loop reference globally
    server_should_run = True  # Enable the updating loop

    try:
        # Create and run the main server task
        server_task = loop.create_task(modbus_server_loop())
        loop.run_until_complete(server_task)
    except asyncio.CancelledError:
        log.info("Modbus server task cancelled")
    finally:
        server_should_run = False  # Ensure loop stops updating
        loop.close()
        log.info("Modbus server stopped")


def start_server():
    """
    Starts the Modbus server in a background daemon thread if not already running.
    """
    global server_thread, server_should_run

    if server_thread and server_thread.is_alive():
        log.warning("Server already running")
        return

    # Start the server in a separate thread
    server_thread = threading.Thread(target=run_server_loop, daemon=True)
    server_thread.start()
    log.info("Server start command issued")


def stop_server():
    """
    Stops the running Modbus server and joins the background thread.
    """
    global server_should_run, server_task, server_loop

    if not server_should_run:
        log.warning("Server is not running")
        return

    server_should_run = False  # Stop updating loop

    if server_loop and server_task:
        # Schedule the cancellation of the server task on the server's event loop
        server_loop.call_soon_threadsafe(server_task.cancel)

    # Wait for server thread to terminate
    if server_thread:
        server_thread.join(timeout=5)
    log.info("Server stop command issued")


def is_server_running():
    """
    Check whether the Modbus server is currently running in its background thread.

    Returns:
        bool: True if the server thread is active, False otherwise.
    """
    return server_thread is not None and server_thread.is_alive()
