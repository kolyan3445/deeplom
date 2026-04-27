"""Configuration for DB and serial."""

DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'admin',
    'password': 'fuckyou',
    'database': 'mydb'
}

SERIAL_CONFIG = {
    'baudrate': 115200,
    'timeout': 1
}

IMAGE_URL = 'http://192.168.0.107/'
WINDOW_SIZE = (1000, 800)
IMAGE_MAX_SIZE = (800, 600)

def get_available_ports():
    """Get list of available COM ports."""
    import serial.tools.list_ports
    return [port.device for port in serial.tools.list_ports.comports()]

COLOR_MAP = {
    'low': '#0000FF',    # blue <20
    'mid_low': '#00FF00', # green 20-30
    'mid_high': '#FFFF00',# yellow 30-40
    'high': '#FF0000'     # red >40
}

