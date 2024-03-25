"""Viewer instance."""

import typing as ty
from weakref import WeakSet

from napari_plot.components.viewer_model import ViewerModel

if ty.TYPE_CHECKING:
    # helpful for IDE support
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
    _window: "Window"
    _instances: ty.ClassVar[WeakSet] = WeakSet()

    def __init__(
        self,
        *,
        title="napari-plot",
        show=True,
    ):
        super().__init__(title=title)
        # having this import here makes all of Qt imported lazily, upon
        # instantiating the first Viewer.
        from napari_plot.window import Window

        self._window = Window(self, show=show)
        self._instances.add(self)

    # Expose private window publicly. This is needed to keep window off pydantic model
    @property
    def window(self) -> "Window":
        """Get window"""
        return self._window

    def screenshot(self, path=None, *, canvas_only=True, flash: bool = True):
        """Take currently displayed screen and convert to an image array.

        Parameters
        ----------
        path : str
            Filename for saving screenshot image.
        canvas_only : bool
            If True, screenshot shows only the image display canvas, and
            if False include the napari viewer frame in the screenshot,
            By default, True.
        flash : bool
            Flag to indicate whether flash animation should be shown after
            the screenshot was captured.
            By default, True.

        Returns
        -------
        image : array
            Numpy array of type ubyte and shape (h, w, 4). Index [0, 0] is the
            upper-left corner of the rendered region.
        """
        return self.window.screenshot(path=path, flash=flash, canvas_only=canvas_only)

    def show(self, *, block=False):
        """Resize, show, and raise the viewer window."""
        self.window.show(block=block)

    def close(self):
        """Close the viewer window."""
        # Remove all the layers from the viewer
        self.layers.clear()
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
        int :
            number of viewer closed.

        """
        # copy to not iterate while changing.
        viewers = [v for v in cls._instances]
        ret = len(viewers)
        for viewer in viewers:
            viewer.close()
        return ret
