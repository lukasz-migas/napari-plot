from qtpy.QtCore import QPoint, Qt
from qtpy.QtGui import QCursor
from qtpy.QtWidgets import QApplication, QDialog, QHBoxLayout, QLayout, QWidget

import napari_plot._qt.helpers as hp


class QtDialog(QDialog):
    """Dialog base class"""

    _icons = None
    _main_layout = None

    def __init__(self, parent=None, title: str = "Dialog"):
        QDialog.__init__(self, parent)
        self._parent = parent
        self.setWindowTitle(QApplication.translate(str(self), title, None, -1))
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.make_gui()

    def on_close(self):
        """Close window"""
        self.close()

    def on_teardown(self) -> None:
        """Execute just before deletion"""

    def closeEvent(self, event):
        """Close event"""
        self._on_teardown()
        return super().closeEvent(event)

    def make_panel(self) -> QLayout:
        """Make panel"""
        ...

    def make_gui(self):
        """Make and arrange main panel"""

        # make panel
        layout = self.make_panel()
        if layout is None:
            raise ValueError("Expected layout")

        # pack element
        self.setLayout(layout)
        self._main_layout = layout

    def show_above_widget(self, widget: QWidget, show: bool = True, y_offset: int = 14):
        """Show popup dialog above the widget"""
        rect = widget.rect()
        pos = widget.mapToGlobal(QPoint(rect.left() + rect.width() / 2, rect.top()))
        sz_hint = self.size()
        pos -= QPoint(sz_hint.width() / 2, sz_hint.height() + y_offset)
        self.move(pos)
        if show:
            self.show()

    def show_above_mouse(self, show: bool = True):
        """Show popup dialog above the mouse cursor position."""
        pos = QCursor().pos()  # mouse position
        sz_hint = self.sizeHint()
        pos -= QPoint(sz_hint.width() / 2, sz_hint.height() + 14)
        self.move(pos)
        if show:
            self.show()

    def show_below_widget(self, widget: QWidget, show: bool = True, y_offset: int = 14):
        """Show popup dialog above the widget"""
        rect = widget.rect()
        pos = widget.mapToGlobal(QPoint(rect.left() + rect.width() / 2, rect.top()))
        sz_hint = self.size()
        pos -= QPoint(sz_hint.width() / 2, -y_offset)
        self.move(pos)
        if show:
            self.show()

    def show_below_mouse(self, show: bool = True):
        """Show popup dialog above the mouse cursor position."""
        pos = QCursor().pos()  # mouse position
        sz_hint = self.sizeHint()
        pos -= QPoint(sz_hint.width() / 2, -14)
        self.move(pos)
        if show:
            self.show()

    def show_right_of_widget(self, widget: QWidget, show: bool = True, x_offset: int = 14):
        """Show popup dialog above the widget"""
        rect = widget.rect()
        pos = widget.mapToGlobal(QPoint(rect.left() + rect.width() / 2, rect.top()))
        sz_hint = self.size()
        pos -= QPoint(-x_offset, sz_hint.height() / 4)
        self.move(pos)
        if show:
            self.show()

    def show_right_of_mouse(self, show: bool = True):
        """Show popup dialog on the right hand side of the mouse cursor position"""
        pos = QCursor().pos()  # mouse position
        sz_hint = self.sizeHint()
        pos -= QPoint(-14, sz_hint.height() / 4)
        self.move(pos)
        if show:
            self.show()

    def show_left_of_widget(self, widget: QWidget, show: bool = True, x_offset: int = 14):
        """Show popup dialog above the widget"""
        rect = widget.rect()
        pos = widget.mapToGlobal(QPoint(rect.left(), rect.top()))
        sz_hint = self.size()
        pos -= QPoint(sz_hint.width() + x_offset, sz_hint.height() / 4)
        self.move(pos)
        if show:
            self.show()

    def show_left_of_mouse(self, show: bool = True):
        """Show popup dialog on the left hand side of the mouse cursor position"""
        pos = QCursor().pos()  # mouse position
        sz_hint = self.sizeHint()
        pos -= QPoint(sz_hint.width() + 14, sz_hint.height() / 4)
        self.move(pos)
        if show:
            self.show()


class QtFramelessPopup(QtDialog):
    """Frameless dialog"""

    # attributes used to move windows around
    _old_window_pos, _move_handle = None, None

    def __init__(
        self,
        parent,
        title="",
        position=None,
        flags=Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Popup,
    ):
        super().__init__(parent, title)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowFlags(flags)
        if position is not None:
            self.move(position)

    def _make_move_handle(self, title: str = "") -> QHBoxLayout:
        """Make handle button that helps move the window around"""
        self._title_label = hp.make_label(self, title, bold=True)
        self._move_handle = hp.make_qta_label(
            self,
            "move",
            tooltip="Click here and drag the mouse around to move the window.",
        )
        self._move_handle.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QHBoxLayout()
        layout.addWidget(self._title_label, stretch=True)
        layout.addWidget(self._move_handle)
        return layout

    def mousePressEvent(self, event):
        """mouse press event"""
        super().mousePressEvent(event)
        # allow movement of the window when user uses right-click and the move handle button does not exist
        if event.button() == Qt.MouseButton.RightButton and self._move_handle is None:
            self._old_window_pos = event.x(), event.y()
        elif self._move_handle is None:
            self._old_window_pos = None
        elif self.childAt(event.pos()) == self._move_handle:
            self._old_window_pos = event.x(), event.y()

    def mouseMoveEvent(self, event):
        """Mouse move event - ensures its possible to move the window to new location"""
        super().mouseMoveEvent(event)
        if self._old_window_pos is not None:
            self.move(
                event.globalX() - self._old_window_pos[0],
                event.globalY() - self._old_window_pos[1],
            )  # noqa

    def mouseReleaseEvent(self, event):
        """mouse release event"""
        super().mouseReleaseEvent(event)
        self._old_window_pos = None


class QtFramelessTool(QtFramelessPopup):
    """Frameless dialog that stays on top"""

    def __init__(
        self,
        parent,
        title: str = "",
        position=None,
        flags=Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool,
    ):
        super().__init__(parent, title, position, flags)
