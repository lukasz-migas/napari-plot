"""Viewer instance."""

from __future__ import annotations

import typing as ty
from pathlib import Path
from weakref import WeakSet

import numpy as np
from napari.utils.events.event_utils import disconnect_events

from napari_plot.components.viewer_model import ViewerModel

# helpful for IDE support
if ty.TYPE_CHECKING:
    from napari_plot._qt.qt_main_window import Window


class Viewer(ViewerModel):
    """Napari ndarray viewer.

    Parameters
    ----------
    title : string, optional
        The title of the viewer window. by default 'napari'.
    show : bool, optional
        Whether to show the viewer after instantiation. by default True.
    """

    # Create private variable for window
    _window: Window = None  # type: ignore
    _instances: ty.ClassVar[WeakSet] = WeakSet()

    def __init__(
        self,
        *,
        title="napari-plot",
        show=True,
        **kwargs: ty.Any,
    ):
        super().__init__(title=title, **kwargs)
        # having this import here makes all of Qt imported lazily, upon
        # instantiating the first Viewer.
        from napari_plot.window import Window

        self._window = Window(self, show=show)
        self._instances.add(self)

    # Expose private window publicly. This is needed to keep window off pydantic model
    @property
    def window(self) -> Window:
        """Get window"""
        return self._window

    def update_console(self, variables):
        """Update console's namespace with desired variables.

        Parameters
        ----------
        variables : dict, str or list/tuple of str
            The variables to inject into the console's namespace.  If a dict, a
            simple update is done.  If a str, the string is assumed to have
            variable names separated by spaces.  A list/tuple of str can also
            be used to give the variable names.  If just the variable names are
            give (list/tuple/str) then the variable values looked up in the
            callers frame.
        """
        if self.window._qt_viewer._console is None:
            self.window._qt_viewer.add_to_console_backlog(variables)
            return
        self.window._qt_viewer.console.push(variables)

    def export_figure(
        self,
        path: str | Path | None = None,
        *,
        scale_factor: float = 1,
        flash: bool = False,
        dpi: int | None = None,
    ) -> np.ndarray:
        """Capture the full plotted data extent and restore the current view.

        The raster image has shape (height, width, 4). Resolution starts at the
        current canvas size and is multiplied by ``scale_factor``. Set ``dpi``
        to change the output density relative to a 96 DPI canvas. An SVG or PDF
        path also writes the corresponding vector figure.
        """
        return self.window.export_figure(path=path, scale=scale_factor, flash=flash, dpi=dpi)

    def export_vector(self, path: str | Path, *, scale_factor: float = 1, dpi: int | None = None) -> None:
        """Export the full data extent as SVG or PDF, preserving line and text geometry."""
        self.window.export_vector(path, scale=scale_factor, dpi=dpi)

    def export_rois(
        self,
        rois: list[np.ndarray],
        paths: str | Path | list[str | Path] | None = None,
        scale: float | None = None,
    ) -> list[np.ndarray]:
        """Capture each region's bounding box from four world-space (y, x) corners.

        Pass a directory to save files as roi_0.png, roi_1.png and so on,
        or pass one destination path per region. Each capture starts at the
        current canvas resolution multiplied by ``scale``.
        """
        return self.window.export_rois(rois, paths=paths, scale=scale)

    def screenshot(
        self,
        path: str | Path | None = None,
        *,
        size: tuple[int, int] | None = None,
        scale: float | None = None,
        canvas_only: bool = True,
        flash: bool = False,
    ) -> np.ndarray:
        """Capture the current view as an RGBA array, optionally saving it to a file.

        ``size`` is a (height, width) in physical pixels. ``size`` and ``scale``
        apply to canvas-only captures.
        """
        return self.window.screenshot(path=path, size=size, scale=scale, flash=flash, canvas_only=canvas_only)

    def show(self, *, block=False):
        """Resize, show, and raise the viewer window."""
        self.window.show(block=block)

    def close(self):
        """Close the viewer window."""
        # Remove all the layers from the viewer
        self.layers.clear()
        # Disconnect changes to dims before removing layers one-by-one
        # to avoid any unnecessary slicing.
        disconnect_events(self.dims.events, self)
        # Close the main window
        self.window.close()
        self._instances.discard(self)

    @classmethod
    def close_all(cls) -> int:
        """
        Class method, Close all existing viewer instances.

        This is mostly exposed to avoid leaking of viewers when running tests.
        As having many non-closed viewer can adversely affect performances.

        It will return the number of viewer closed.

        Returns
        -------
        int
            number of viewer closed.

        """
        # copy to not iterate while changing.
        viewers = list(cls._instances)
        ret = len(viewers)
        for viewer in viewers:
            viewer.close()
        return ret


def current_viewer() -> Viewer | None:
    """Return the currently active napari viewer."""
    try:
        from napari._qt.qt_main_window import _QtMainWindow
    except ImportError:
        return None
    else:
        return _QtMainWindow.current_viewer()
