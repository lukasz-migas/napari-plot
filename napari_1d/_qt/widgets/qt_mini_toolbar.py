"""Mini toolbar"""
# Standard library imports
from typing import Callable, Optional

from qtpy.QtCore import Qt

# Third-party imports
from qtpy.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget

from napari_1d._qt.helpers import make_h_spacer, make_svg_btn, make_v_spacer


class QtMiniToolbar(QFrame):
    """Mini toolbar"""

    def __init__(self, parent, orientation: Qt.Horizontal, max_size: int = 25):
        super().__init__(parent)
        self._icons = None
        self._tools = {}
        self.orientation = orientation

        self.layout = QHBoxLayout() if orientation == Qt.Horizontal else QVBoxLayout()
        self.layout.addSpacerItem(
            make_h_spacer() if orientation == Qt.Horizontal else make_v_spacer()
        )
        self.layout.setSpacing(0)
        self.layout.setMargin(0)
        self.setLayout(self.layout)
        self.setMaximumHeight(
            max_size
        ) if orientation == Qt.Horizontal else self.setMaximumWidth(max_size)

    @property
    def n_items(self) -> int:
        """Return the number of items in the layout"""
        return self.layout.count()

    def insert_svg_tool(
        self,
        object_name: str,
        flat: bool = True,
        func: Optional[Callable] = None,
        tooltip: str = None,
        set_checkable: bool = False,
        check: bool = False,
    ):
        """Insert tool"""
        btn = make_svg_btn(self, object_name, "", tooltip=tooltip, flat=flat)
        btn.setMaximumSize(10, 10)
        if callable(func):
            btn.clicked.connect(func)
        if set_checkable:
            btn.setCheckable(True)
        if check:
            btn.setChecked(True)
        self._tools[object_name] = btn
        self.layout.insertWidget(0, btn, alignment=Qt.AlignCenter)
        return btn


if __name__ == "__main__":
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
