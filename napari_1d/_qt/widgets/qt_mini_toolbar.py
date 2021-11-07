"""Mini toolbar"""
import typing as ty

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget

from .. import helpers as hp


class QtMiniToolbar(QFrame):
    """Mini toolbar"""

    def __init__(self, parent, orientation: Qt.Horizontal, max_size: int = 25):
        super().__init__(parent)
        self._icons = None
        self._tools = {}
        self.orientation = orientation

        self.layout = QHBoxLayout() if orientation == Qt.Horizontal else QVBoxLayout()
        self.layout.addSpacerItem(hp.make_h_spacer() if orientation == Qt.Horizontal else hp.make_v_spacer())
        self.layout.setSpacing(0)
        self.layout.setMargin(0)
        self.setLayout(self.layout)
        self.setMaximumHeight(max_size) if orientation == Qt.Horizontal else self.setMaximumWidth(max_size)

    @property
    def n_items(self) -> int:
        """Return the number of items in the layout"""
        return self.layout.count()

    def insert_svg_tool(
        self,
        object_name: str,
        flat: bool = True,
        func: ty.Optional[ty.Callable] = None,
        tooltip: str = None,
        checkable: bool = False,
        check: bool = False,
    ):
        """Insert tool"""
        btn = hp.make_svg_btn(self, object_name, "", tooltip=tooltip, flat=flat)
        btn.setMaximumSize(10, 10)
        if callable(func):
            btn.clicked.connect(func)
        if checkable:
            btn.setCheckable(True)
        if check:
            btn.setChecked(True)
        self._tools[object_name] = btn
        self.layout.insertWidget(0, btn, alignment=Qt.AlignCenter)
        return btn

    def insert_qta_tool(
        self,
        name: str,
        flat: bool = True,
        func: ty.Optional[ty.Callable] = None,
        tooltip: str = None,
        checkable: bool = False,
        check: bool = False,
    ):
        """Insert tool"""
        btn = hp.make_qta_btn(self, name, tooltip=tooltip, flat=flat, medium=False, size=(26, 26))
        if callable(func):
            btn.clicked.connect(func)
        if checkable:
            btn.setCheckable(True)
        if check:
            btn.setChecked(True)
        self._tools[name] = btn
        self.layout.insertWidget(0, btn, alignment=Qt.AlignCenter)
        return btn


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtpy.QtWidgets import QApplication

    app = QApplication(sys.argv)
    frame = QWidget()
    ha = QHBoxLayout()
    frame.setLayout(ha)

    h = QtMiniToolbar(None, orientation=Qt.Horizontal)
    h.insert_svg_tool("save")
    h.insert_svg_tool("extract")
    h.insert_svg_tool("add")

    ha.addWidget(h)
    frame.show()
    sys.exit(app.exec_())
