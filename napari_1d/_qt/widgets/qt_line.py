"""Horizontal and Vertical lines"""
from qtpy.QtWidgets import QFrame


class QtHorzLine(QFrame):
    """Horizontal line"""

    def __init__(self, parent):
        super().__init__(parent=parent)
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)


class QtVertLine(QFrame):
    """Vertical line"""

    def __init__(self, parent):
        super().__init__(parent=parent)
        self.setFrameShape(QFrame.VLine)
        self.setFrameShadow(QFrame.Sunken)