from qtpy.QtWidgets import QPushButton
from qtpy.QtCore import Signal, Qt


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
