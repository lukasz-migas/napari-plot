"""Mini toolbar"""
import typing as ty

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout

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
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        self.setMaximumHeight(max_size) if orientation == Qt.Horizontal else self.setMaximumWidth(max_size)

    @property
    def n_items(self) -> int:
        """Return the number of items in the layout"""
        return self.layout.count()

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
        btn = hp.make_qta_btn(self, name, tooltip=tooltip, flat=flat, size_name="small", size=(26, 26))
        if callable(func):
            btn.clicked.connect(func)
        btn.setCheckable(checkable)
        if check:
            btn.setChecked(True)
        self._tools[name] = btn
        self.layout.insertWidget(0, btn, alignment=Qt.AlignCenter)
        return btn
