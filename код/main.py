import sys
import io
import requests
import base64
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QDialog, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
                             QSplitter, QWidget, QMessageBox, QHeaderView, QLabel)
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QFont
from PyQt6.QtCore import QTimer, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PIL import Image
from config import IMAGE_URL, WINDOW_SIZE, IMAGE_MAX_SIZE, COLOR_MAP, get_available_ports
from database import ensure_table, list_sessions, save_session, load_session
from serial_reader import SerialReader

class ImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.pixmap() or not self.parent.points:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = QFont()
        font.setPixelSize(12)
        painter.setFont(font)
        w = self.pixmap().width()
        h = self.pixmap().height()
        scale_x = w / 1600.0
        scale_y = h / 1200.0
        for point in self.parent.points:
            x = point['point']['x'] * scale_x
            y = point['point']['y'] * scale_y
            temp = point['point']['temp']
            if temp < 20:
                color = COLOR_MAP['low']
            elif temp < 30:
                color = COLOR_MAP['mid_low']
            elif temp < 40:
                color = COLOR_MAP['mid_high']
            else:
                color = COLOR_MAP['high']
            pen = QPen(QColor(color), 3)
            painter.setPen(pen)
            painter.drawEllipse(int(x-10), int(y-10), 20, 20)
            painter.drawText(int(x+15), int(y+5), f"{temp:.1f}°C")
        painter.end()

class StartupDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Temperature Monitoring - Choose Session")
        self.setMinimumSize(500, 300)
        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Time", "Temp"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.new_btn = QPushButton("New Session")
        self.new_btn.clicked.connect(self.new_session)
        self.load_btn = QPushButton("Load Session")
        self.load_btn.clicked.connect(self.load_session)
        btn_layout.addWidget(self.new_btn)
        btn_layout.addWidget(self.load_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.refresh_sessions()

    def refresh_sessions(self):
        sessions = list_sessions()
        self.table.setRowCount(len(sessions))
        for row, (sid, stime, temp) in enumerate(sessions):
            self.table.setItem(row, 0, QTableWidgetItem(str(sid)))
            self.table.setItem(row, 1, QTableWidgetItem(str(stime)))
            self.table.setItem(row, 2, QTableWidgetItem(f"{temp:.1f}°C"))

    def new_session(self):
        self.main_window = MainWindow(new=True)
        self.main_window.show()
        self.close()

    def load_session(self):
        row = self.table.currentRow()
        if row >= 0:
            sid = int(self.table.item(row, 0).text())
            self.main_window = MainWindow(session_id=sid)
            self.main_window.show()
            self.close()

class MainWindow(QMainWindow):
    def __init__(self, new=False, session_id=None):
        super().__init__()
        self.setWindowTitle("Temperature Monitoring")
        self.setFixedSize(*WINDOW_SIZE)
        self.points = []
        self.times = []
        self.temps = []
        self.serial_port = None
        self.serial_thread = None
        self.is_new = new
        self.loaded_id = session_id

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        controls = QHBoxLayout()
        self.port_combo = QComboBox()
        self.refresh_ports()
        controls.addWidget(QLabel("Port:"))
        controls.addWidget(self.port_combo)
        refresh_ports_btn = QPushButton("Refresh Ports")
        refresh_ports_btn.clicked.connect(self.refresh_ports)
        controls.addWidget(refresh_ports_btn)
        self.start_btn = QPushButton("Start Serial")
        self.start_btn.clicked.connect(self.toggle_serial)
        controls.addWidget(self.start_btn)
        self.save_btn = QPushButton("Save Session")
        self.save_btn.clicked.connect(self.save)
        controls.addWidget(self.save_btn)
        refresh_img_btn = QPushButton("Refresh Image")
        refresh_img_btn.clicked.connect(self.update_image)
        controls.addWidget(refresh_img_btn)
        controls.addStretch()
        layout.addLayout(controls)

        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter)

        self.image_label = ImageLabel(self)
        self.image_label.setMinimumHeight(IMAGE_MAX_SIZE[1])
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid black;")
        splitter.addWidget(self.image_label)

        self.figure = Figure(figsize=(10, 5))
        self.canvas = FigureCanvas(self.figure)
        splitter.addWidget(self.canvas)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Temp (°C)")
        self.ax.grid(True)

        splitter.setSizes([IMAGE_MAX_SIZE[1], 350])

        if session_id:
            session_data = load_session(session_id)
            self.points = session_data['points']
            if session_data.get('image_base64'):
                pixmap = QPixmap()
                pixmap.loadFromData(base64.b64decode(session_data['image_base64']))
                self.image_label.setPixmap(pixmap)
            self.times = [p['time'] for p in self.points]
            self.temps = [p['point']['temp'] for p in self.points]
            self.update_plot()

        if new:
            ensure_table()

        self.update_image()

    def refresh_ports(self):
        ports = get_available_ports()
        self.port_combo.clear()
        self.port_combo.addItems(ports or ["No ports"])

    def toggle_serial(self):
        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.stop()
            self.serial_thread.wait()
            self.start_btn.setText("Start Serial")
        else:
            port = self.port_combo.currentText()
            if port == "No ports":
                QMessageBox.warning(self, "Error", "No serial port selected.")
                return
            self.serial_port = port
            self.serial_thread = SerialReader(port)
            self.serial_thread.new_point.connect(self.add_point)
            self.serial_thread.start()
            self.start_btn.setText("Stop Serial")

    def add_point(self, point):
        self.points.append(point)
        self.times.append(point['time'])
        self.temps.append(point['point']['temp'])
        self.update_plot()
        self.image_label.update()

    def update_image(self):
        try:
            resp = requests.get(IMAGE_URL, timeout=5)
            img = Image.open(io.BytesIO(resp.content))
            img.thumbnail(IMAGE_MAX_SIZE, Image.Resampling.LANCZOS)
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            pixmap = QPixmap()
            pixmap.loadFromData(img_byte_arr.read())
            self.image_label.setPixmap(pixmap)
            self.image_label.update()
        except Exception as e:
            print(f"Image update error: {e}")

    def update_plot(self):
        self.ax.clear()
        if self.times:
            self.ax.plot(self.times, self.temps, 'b.-')
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Temp (°C)")
        self.figure.tight_layout()
        self.canvas.draw()

    def save(self):
        if not self.points:
            QMessageBox.warning(self, "Error", "No points to save.")
            return
        sid = save_session(self.points)
        if sid:
            QMessageBox.information(self, "Success", f"Saved session ID: {sid}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ensure_table()
    dialog = StartupDialog()
    dialog.show()
    sys.exit(app.exec())

