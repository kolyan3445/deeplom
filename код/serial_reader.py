import sys
import json
import serial
from PyQt6.QtCore import QThread, pyqtSignal
from config import SERIAL_CONFIG

class SerialReader(QThread):
    new_point = pyqtSignal(dict)  # emits {'time': , 'point': {'x':, 'y':, 'temp':}}

    def __init__(self, port):
        super().__init__()
        self.port = port
        self.running = False
        self.ser = None

    def run(self):
        try:
            self.ser = serial.Serial(self.port, **SERIAL_CONFIG)
            self.running = True
            while self.running:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8').strip()
                    if line:
                        point = json.loads(line)
                        self.new_point.emit(point)
        except Exception as e:
            print(f"Serial error: {e}")

    def stop(self):
        self.running = False
        if self.ser:
            self.ser.close()

