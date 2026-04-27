from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QPainter, QPen, QColor, QFont
from PyQt6.QtCore import Qt
from config import COLOR_MAP, IMAGE_MAX_SIZE

class ImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent  # MainWindow for points access

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.pixmap() or not self.parent.points:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = QFont()
        font.setPixelSize(12)
        painter.setFont(font)
        w, h = self.pixmap().width(), self.pixmap().height()
        scale_x = w / 1600.0  # Original image size assumption
        scale_y = h / 1200.0
        for point in self.parent.points:
            x = point['point']['x'] * scale_x
            y = point['point']['y'] * scale_y
            temp = point['point']['temp']
            if temp < 20:
                color_name = 'low'
            elif temp < 30:
                color_name = 'mid_low'
            elif temp < 40:
                color_name = 'mid_high'
            else:
                color_name = 'high'
            color = COLOR_MAP[color_name]
            pen = QPen(QColor(color), 3)
            painter.setPen(pen)
            painter.drawEllipse(int(x-10), int(y-10), 20, 20)
            painter.drawText(int(x+15), int(y+5), f"{temp:.1f}")
        painter.end()

