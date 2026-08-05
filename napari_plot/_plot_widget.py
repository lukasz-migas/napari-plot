"""Dock widget"""

from contextlib import ExitStack, suppress

from napari.utils.theme import _themes, get_theme
from qtextra.config import THEMES
from qtextra.helpers import get_parent
from qtpy.QtWidgets import QVBoxLayout, QWidget

from napari_plot._qt.qt_viewer import QtViewer
from napari_plot.components.viewer_model import ViewerModel as ViewerModelPlot
from napari_plot.resources import get_stylesheet, load_assets


def _synchronize_qtextra_theme(theme_name: str) -> None:
    """Set qtextra's theme without changing napari's registered themes."""
    if THEMES.theme == theme_name:
        return

    napari_icon_colors = {name: theme.icon for name, theme in _themes.items()}
    with ExitStack() as stack:
        for theme in _themes.values():
            stack.enter_context(theme.events.icon.blocker())
        try:
            THEMES.theme = theme_name
        finally:
            for name, color in napari_icon_colors.items():
                if name in _themes:
                    _themes[name].icon = color


class NapariPlotWidget(QWidget):
    """Create instance of napari-plot Viewer."""

    def __init__(self, napari_viewer):
        parent = get_parent(None)
        super().__init__(parent)
        load_assets()
        self.viewer = napari_viewer
        self.viewer_plot = ViewerModelPlot()
        self._update_theme()
        self.qt_viewer = QtViewer(self.viewer_plot, parent=parent)

        layout = QVBoxLayout(self)
        layout.addWidget(self.qt_viewer, stretch=True)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.viewer.events.theme.connect(self._update_theme)

    def _update_theme(self, event=None) -> None:
        """Apply the host napari theme to the embedded plotting widget."""
        host_theme = str(getattr(event, "value", self.viewer.theme))
        qtextra_theme = host_theme
        if qtextra_theme not in THEMES.available_themes():
            qtextra_theme = get_theme(host_theme).type
        _synchronize_qtextra_theme(qtextra_theme)
        self.viewer_plot.theme = host_theme
        self.setStyleSheet(get_stylesheet(qtextra_theme))

    def closeEvent(self, event) -> None:
        """Disconnect host-viewer events before closing the widget."""
        with suppress(ValueError):
            self.viewer.events.theme.disconnect(self._update_theme)
        super().closeEvent(event)
