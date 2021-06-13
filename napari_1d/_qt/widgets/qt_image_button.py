from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QPushButton


class QtImagePushButton(QPushButton):
    """Image button"""

    evt_click = Signal(QPushButton)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def mousePressEvent(self, evt) -> None:
        """Mouse press event"""
        if evt.button() == Qt.LeftButton:
            self.evt_click.emit(self)
        super().mousePressEvent(evt)
