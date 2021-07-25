"""QtIconLabel"""
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QLabel


class QtIconLabel(QLabel):
    """Label with icon"""

    evt_clicked = Signal()

    def __init__(self, object_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMouseTracking(True)
        self.setObjectName(object_name)

    def mousePressEvent(self, ev):
        """Mouse press event"""
        if ev.button() == Qt.LeftButton:
            self.evt_clicked.emit()
        super().mousePressEvent(ev)
