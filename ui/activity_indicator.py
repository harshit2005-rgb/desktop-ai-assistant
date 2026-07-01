import math

from PySide6.QtCore import QPointF, QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class ActivityIndicator(QWidget):
    """A small animated blue indicator used while the AI is busy."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedSize(14, 14)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._angle = 0.0
        self._radius = 4.0

        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._advance)

        self.hide()

    def start_activity(self):
        if self.timer.isActive():
            return

        self._angle = 0.0
        self.show()
        self.timer.start()

    def stop_activity(self):
        self.timer.stop()
        self.hide()

    def _advance(self):
        self._angle = (self._angle + 0.18) % (2 * math.pi)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        center = QPointF(self.width() / 2, self.height() / 2)
        dot_x = center.x() + self._radius * math.cos(self._angle)
        dot_y = center.y() + self._radius * math.sin(self._angle)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#00C2FF"))
        painter.drawEllipse(QPointF(dot_x, dot_y), 2.2, 2.2)

        ring_pen = QPen(QColor("#00C2FF"))
        ring_pen.setWidth(1)
        painter.setPen(ring_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QRectF(1.2, 1.2, 11.6, 11.6))
