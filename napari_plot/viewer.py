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
        path: ty.Optional[str] = None,
        *,
        scale_factor: float = 1,
        flash: bool = False,
    ) -> np.ndarray:
        """Export an image of the full extent of the displayed layer data.

        This function finds a tight boundary around the data, resets the view
        around that boundary, takes a screenshot for which each pixel is equal
        to the pixel resolution of the data, then restores the previous zoom
        and canvas sizes.

        The pixel resolution can be upscaled or downscaled by the given
        `scale_factor`. For example, an image with 800 x 600 pixels with
        scale_factor 1 will be saved as 800 x 600, or 1200 x 900 with
        scale_factor 1.5.

        For anisotropic images, the resolution is set by the highest-resolution
        dimension. For an anisotropic 800 x 600 image with scale set to
        [0.25, 0.5], the screenshot will be 800 x 1200, or 1200 x 1800 with a
        scale_factor of 1.5.

        Upscaling will be done using the interpolation mode set on each layer.

        Parameters
        ----------
        path : str, optional
            Filename for saving screenshot image.
        scale_factor : float
            By default, the zoom will export approximately 1 pixel per
            smallest-scale pixel on the viewer. For example, if a layer has
            scale 0.004nm/pixel and another has scale 1µm/pixel, the exported
            figure will have 0.004nm/pixel. Upscaling by 2 will produce a
            figure with 0.002nm/pixel through the interpolation mode set on
            each layer.
        flash : bool
            Flag to indicate whether flash animation should be shown after
            the screenshot was captured. By default, False.

        Returns
        -------
        image : array
            Numpy array of type ubyte and shape (h, w, 4). Index [0, 0] is the
            upper-left corner of the rendered region.
        """
        return self.window.export_figure(
            path=path,
            scale=scale_factor,
            flash=flash,
        )

    def export_rois(
        self,
        rois: list[np.ndarray],
        paths: ty.Optional[ty.Union[str, Path, list[ty.Union[str, Path]]]] = None,
        scale: ty.Optional[float] = None,
    ):
        """Export the given rectangular rois to specified file paths.

        Iteratively take a screenshot of each given roi. Note that 3D rois
        or taking rois when number of dimensions displayed in the viewer
        canvas is 3, is currently not supported.

        Parameters
        ----------
        rois: numpy array
            A list of arrays with each having shape (4, 2) representing a
            rectangular roi.
        paths: str, Path, list[str, Path], optional
            Where to save the rois. If a string or a Path, a directory will
            be created if it does not exist yet and screenshots will be saved
            with filename `roi_{n}.png` where n is the nth roi. If paths is
            a list of either string or paths, these need to be the full paths
            of where to store each individual roi. In this case
            the length of the list and the number of rois must match.
            If None, the screenshots will only be returned
            and not saved to disk.
        scale: float, optional
            Scale factor used to increase resolution of canvas for the screenshot.
            By default, uses the displayed scale.

        Returns
        -------
        screenshot_list: list
            The list containing all the screenshots.
        """
        # Check to see if roi has shape (n,2,2)
        if any(roi.shape[-2:] != (4, 2) for roi in rois):
            raise ValueError(
                "ROI found with invalid shape, all rois must have shape (4, 2), i.e. have 4 corners defined in 2 "
                "dimensions. 3D is not supported."
            )

        screenshot_list = self.window.export_rois(rois, paths=paths, scale=scale)

        return screenshot_list

    def screenshot(
        self,
        path: ty.Optional[str] = None,
        *,
        size: ty.Optional[tuple[str, str]] = None,
        scale: ty.Optional[float] = None,
        canvas_only: bool = True,
        flash: bool = False,
    ):
        """Take currently displayed screen and convert to an image array.

        Parameters
        ----------
        path : str, optional
            Filename for saving screenshot image.
        size : tuple of two ints, optional
            Size (resolution height x width) of the screenshot. By default, the currently
            displayed size. Only used if `canvas_only` is True.
        scale : float, optional
            Scale factor used to increase resolution of canvas for the screenshot.
            By default, the currently displayed resolution.Only used if `canvas_only` is
            True.
        canvas_only : bool
            If True, screenshot shows only the image display canvas, and if False include
            the napari viewer frame in the screenshot, By default, True.
        flash : bool
            Flag to indicate whether flash animation should be shown after
            the screenshot was captured.
            By default, False.

        Returns
        -------
        image : array
            Numpy array of type ubyte and shape (h, w, 4). Index [0, 0] is the
            upper-left corner of the rendered region.
        """
        return self.window.screenshot(
            path=path,
            size=size,
            scale=scale,
            flash=flash,
            canvas_only=canvas_only,
        )

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


def current_viewer() -> ty.Optional[Viewer]:
    """Return the currently active napari viewer."""
    try:
        from napari._qt.qt_main_window import _QtMainWindow
    except ImportError:
        return None
    else:
        return _QtMainWindow.current_viewer()
