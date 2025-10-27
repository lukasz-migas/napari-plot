from __future__ import annotations

from napari.utils.translations import trans
from qtpy.QtCore import QSize, Qt, Signal
from qtpy.QtGui import QPainter
from qtpy.QtWidgets import QLabel, QStackedWidget, QStyle, QStyleOption, QVBoxLayout, QWidget


class QtWelcomeLabel(QLabel):
    """Labels used for main message in welcome page."""


class QtShortcutLabel(QLabel):
    """Labels used for displaying shortcu information in welcome page."""


class QtWelcomeWidget(QWidget):
    """Welcome widget to display initial information and shortcuts to user."""

    sig_dropped = Signal("QEvent")

    def __init__(self, parent) -> None:
        super().__init__(parent)

        # Create colored icon using theme
        self._image = QLabel()
        self._image.setObjectName("logo_silhouette_plot")
        self._image.setMinimumSize(300, 300)
        self._label = QtWelcomeLabel(trans._("Welcome to napari-plot!"))

        # Widget setup
        self.setAutoFillBackground(True)
        self.setAcceptDrops(True)
        self._image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Layout
        text_layout = QVBoxLayout()
        text_layout.addWidget(self._label)

        layout = QVBoxLayout()
        layout.addStretch()
        layout.setSpacing(30)
        layout.addWidget(self._image)
        layout.addLayout(text_layout)
        layout.addStretch()

        self.setLayout(layout)

    def minimumSizeHint(self):
        """
        Overwrite minimum size to allow creating small viewer instance
        """
        return QSize(100, 100)

    def paintEvent(self, event):
        """Override Qt method.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        option = QStyleOption()
        option.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, option, p, self)

    def _update_property(self, prop, value):
        """Update properties of widget to update style.

        Parameters
        ----------
        prop : str
            Property name to update.
        value : bool
            Property value to update.
        """
        self.setProperty(prop, value)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event):
        """Override Qt method.

        Provide style updates on event.

        Parameters
        ----------
        event : qtpy.QtCore.QDragEnterEvent
            Event from the Qt context.
        """
        self._update_property("drag", True)
        if event.mimeData().hasUrls():
            viewer = self.parentWidget().nativeParentWidget()._qt_viewer
            viewer._set_drag_status()
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """Override Qt method.

        Provide style updates on event.

        Parameters
        ----------
        event : qtpy.QtCore.QDragLeaveEvent
            Event from the Qt context.
        """
        self._update_property("drag", False)

    def dropEvent(self, event):
        """Override Qt method.

        Provide style updates on event and emit the drop event.

        Parameters
        ----------
        event : qtpy.QtCore.QDropEvent
            Event from the Qt context.
        """
        self._update_property("drag", False)
        self.sig_dropped.emit(event)


class QtWidgetOverlay(QStackedWidget):
    """
    Stacked widget providing switching between the widget and a welcome page.
    """

    sig_dropped = Signal("QEvent")
    resized = Signal()
    leave = Signal()
    enter = Signal()

    def __init__(self, parent, widget) -> None:
        super().__init__(parent)

        self._overlay = QtWelcomeWidget(self)

        # Widget setup
        self.addWidget(widget)
        self.addWidget(self._overlay)
        self.setCurrentIndex(0)

        # Signals
        self._overlay.sig_dropped.connect(self.sig_dropped)

    def set_welcome_visible(self, visible=True):
        """Show welcome screen widget on stack."""
        self.setCurrentIndex(int(visible))

    def resizeEvent(self, event):
        """Emit our own event when canvas was resized."""
        self.resized.emit()
        return super().resizeEvent(event)

    def enterEvent(self, event):
        """Emit our own event when mouse enters the canvas."""
        self.enter.emit()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Emit our own event when mouse leaves the canvas."""
        self.leave.emit()
        super().leaveEvent(event)
