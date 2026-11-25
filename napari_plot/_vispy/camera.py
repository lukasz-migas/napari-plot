"""Camera model"""

from __future__ import annotations

import typing as ty

import numpy as np
from napari._vispy.camera import add_mouse_pan_zoom_toggles
from vispy.geometry import Rect

from napari_plot._vispy.components.camera import LimitedPanZoomCamera
from napari_plot.components.axis import AxisScale, transform_axis_values

if ty.TYPE_CHECKING:
    from collections.abc import Sequence

    from napari.layers import Layer

    from napari_plot.components.camera import Camera
    from napari_plot.components.canvas import PlotGridCell
    from napari_plot.components.viewer_model import ViewerModel

RectLimits = tuple[float, float, float, float]


class VispyCamera:
    """Vispy camera.

    Parameters
    ----------
    view : vispy.scene.widgets.viewbox.ViewBox
        Viewbox for current scene.
    camera : napari.components.Camera
        napari camera model.
    viewer :
        instance of the viewer class
    follow_model : bool
        When True, the camera starts from the model state without writing its own default state back, so adding a
        camera (e.g. for another plot cell in grid mode) does not reset the view of the others.

    """

    # ids of camera models whose zoom is being published by a drawn camera. Plot cells in grid mode share one model,
    # and a published zoom must not come back to any of them: the zoom setter scales both axes equally, which would
    # undo zooming a single axis.
    _publishing_zoom: ty.ClassVar[set[int]] = set()
    _cell: PlotGridCell | None = None

    def __init__(self, view, camera: Camera, viewer: ViewerModel, follow_model: bool = False):
        self._view = view
        self._camera = camera
        self._viewer = viewer
        # rect last exchanged with the model; several cameras can follow one model (grid mode) and only the camera
        # whose rect changed since then may write it back
        self._synced_rect: tuple[float, float, float, float] | None = None
        self._applying = False
        self._initializing = follow_model
        self._layers: Sequence[Layer] | None = None
        self._shared = (True, True)
        self._local_extent: RectLimits | None = None
        self._local_rect: RectLimits | None = None
        self._autoscaling = False

        # Create camera
        self._view.camera = MouseToggledLimitedPanZoomCamera(
            viewer=self._viewer, aspect=camera.aspect, to_data=self.to_data
        )
        self._view.camera.viewbox_key_event = viewbox_key_event

        # connect events
        self._camera.events.mouse_pan.connect(self._on_mouse_toggles_change)
        self._camera.events.mouse_zoom.connect(self._on_mouse_toggles_change)
        self._camera.events.aspect.connect(self._on_aspect_change)
        self._camera.events.zoom.connect(self._on_zoom_change)
        self._camera.events.rect.connect(self._on_rect_change)
        self._camera.events.extent.connect(self._on_extent_change)
        self._camera.events.x_range.connect(self._on_range_change)
        self._camera.events.y_range.connect(self._on_range_change)
        self._camera.events.axis_mode.connect(self._on_axis_mode_change)
        self._camera.events.extent_mode.connect(self._on_extent_mode_change)
        self._camera.events.force_rect.connect(self._on_force_rect_change)
        # A cell added in grid mode must publish its new bounds before auto-zoom handlers read them.
        self._camera.events.zoomed.connect(self._on_sync_rect, position="first")

        self._on_axis_mode_change(None)
        self._on_extent_mode_change(None)
        self._initializing = False
        self._on_rect_change(None)

    @property
    def camera(self):
        """Return camera instance."""
        return self._view.camera

    @property
    def zoom(self):
        """float: Scale from canvas pixels to world pixels."""
        canvas_size = np.array(self._view.canvas.size)
        scale = np.array([self._view.camera.rect.width, self._view.camera.rect.height])
        scale[np.isclose(scale, 0)] = 1  # fix for #2875
        zoom = np.min(canvas_size / scale)
        return zoom

    @zoom.setter
    def zoom(self, zoom):
        if self.zoom == zoom:
            return
        scale = np.array(self._view.canvas.size) / zoom
        # Set view rectangle, as left, right, width, height
        corner = np.subtract(self._view.camera.center[:2], scale / 2)
        display_rect = (
            corner[0],
            corner[0] + scale[0],
            corner[1],
            corner[1] + scale[1],
        )
        self.rect = self._transform_rect(display_rect, inverse=True)

    def _transform_rect(
        self,
        rect: Rect | ty.Iterable[float],
        *,
        inverse: bool,
    ) -> tuple[float, float, float, float]:
        """Transform a camera rectangle between data and display coordinates."""
        values = (rect.left, rect.right, rect.bottom, rect.top) if isinstance(rect, Rect) else tuple(rect)
        xmin, xmax, ymin, ymax = values
        low = self._transform_position(xmin, ymin, inverse=inverse)
        high = self._transform_position(xmax, ymax, inverse=inverse)
        return low[0], high[0], low[1], high[1]

    def axis_scale(self, name: ty.Literal["x", "y"]) -> AxisScale:
        """Return the selected scale for this view, including a grid cell override."""
        axis = self._viewer.axis
        return self._cell.axis_scale(name, axis) if self._cell is not None else getattr(axis, f"{name}_scale")

    def _transform_position(self, x: float, y: float, *, inverse: bool) -> tuple[float, float]:
        axis = self._viewer.axis
        return (
            transform_axis_values(x, self.axis_scale("x"), inverse=inverse, power=axis.x_power),
            transform_axis_values(y, self.axis_scale("y"), inverse=inverse, power=axis.y_power),
        )

    def to_data(self, x: float, y: float) -> tuple[float, float]:
        """Convert coordinates from the displayed plane to the data plane."""
        return self._transform_position(x, y, inverse=True)

    def configure_cell(
        self,
        cell: PlotGridCell | None,
        layers: Sequence[Layer] | None,
        shared: tuple[bool, bool],
        *,
        reset: tuple[bool, bool] = (False, False),
    ) -> None:
        """Apply per-cell axis settings and recompute its local data bounds."""
        previous_extent = self._local_extent
        previous_rect = self._local_rect
        previous_shared = self._shared
        previous_cell = self._cell
        self._cell, self._layers, self._shared = cell, layers, shared
        self._local_extent = (
            self._viewer._get_rect_extent(layers=layers, cell=cell, use_camera_range=False)
            if layers is not None and not all(shared)
            else None
        )
        if self._local_extent is not None and self._joint_autoscale:
            self._local_extent = self._with_value_headroom(self._local_extent)
        self._local_rect = self._local_extent
        if (
            self._local_extent is not None
            and previous_extent is not None
            and previous_rect is not None
            and previous_cell is cell
        ):
            values = list(self._local_extent)
            for i in (0, 1):
                part = slice(i * 2, i * 2 + 2)
                was_fitted = self._viewer.autoscale and np.allclose(
                    previous_rect[part], previous_extent[part], rtol=1e-12, atol=1e-10
                )
                if not shared[i] and not previous_shared[i] and not reset[i] and not was_fitted:
                    values[part] = previous_rect[part]
            self._local_rect = tuple(values)
        self.camera.locked_axis = self._value_axis() if self._joint_autoscale else None
        self._on_extent_change(None)
        self._on_force_rect_change(None)
        self._update_flip()

    def refresh_bounds(self) -> None:
        """Recompute the cell's local data bounds after its layers' data changed, keeping its other settings."""
        if self._layers is not None:
            self.configure_cell(self._cell, self._layers, self._shared)

    def _value_axis(self) -> int | None:
        """Index (0 = x, 1 = y) of the only independent axis of a joint marginal, or None."""
        if self._shared == (True, False):
            return 1
        if self._shared == (False, True):
            return 0
        return None

    @property
    def _joint_autoscale(self) -> bool:
        """Whether this is a joint marginal whose value axis follows the data visible in its shared range."""
        grid = self._viewer.canvas.grid
        return bool(
            grid.enabled
            and grid.joint
            and grid.joint_autoscale
            and self._layers is not None
            and self._value_axis() is not None
        )

    def _with_value_headroom(self, extent: RectLimits) -> RectLimits:
        """Widen the value axis of an autoscaled marginal's extent to its fit of all the data.

        The fit pads the data away from zero; without this the extent would clip that padding when the visible data
        holds the largest value.
        """
        value_axis = self._value_axis()
        fit = self._viewer._get_value_range_in_region(self._layers, 1 - value_axis, -np.inf, np.inf)
        if fit is None:
            return extent
        values = list(extent)
        start = value_axis * 2
        values[start : start + 2] = min(values[start], fit[0]), max(values[start + 1], fit[1])
        return tuple(values)

    def _autoscale_rect(self, rect: RectLimits) -> RectLimits:
        """Fit the value axis of a joint marginal to its data inside the shared range of ``rect``."""
        value_axis = self._value_axis()
        if not self._joint_autoscale or value_axis is None:
            return rect
        shared = 1 - value_axis
        lo, hi = sorted(rect[shared * 2 : shared * 2 + 2])
        fit = self._viewer._get_value_range_in_region(self._layers, shared, lo, hi)
        if fit is None:
            return rect
        values = list(rect)
        values[value_axis * 2 : value_axis * 2 + 2] = fit
        return tuple(values)

    def _update_flip(self) -> None:
        """Apply axis direction independently of the canonical camera limits."""
        axis = self._viewer.axis
        flips = [axis.x_inverted, axis.y_inverted]
        if self._viewer.canvas.grid.enabled and self._viewer.canvas.grid.joint:
            flips = [flip if shared else False for flip, shared in zip(flips, self._shared, strict=True)]
        for index, name in enumerate(("x", "y")):
            limits = getattr(self._cell, f"{name}lim", None)
            if not self._shared[index] and limits is not None:
                flips[index] = limits[0] > limits[1]
        self.camera.flip = (*flips, False)

    def reset_cell_axis(self, name: ty.Literal["x", "y"]) -> bool:
        """Restore one independent axis to its fit limits, or return False if it is shared."""
        index = 0 if name == "x" else 1
        if self._shared[index] or self._local_extent is None or self._local_rect is None:
            return False
        start = index * 2
        self._local_rect = (
            *self._local_rect[:start],
            *self._local_extent[start : start + 2],
            *self._local_rect[start + 2 :],
        )
        self._on_rect_change(None)
        return True

    def restore_cell_rect(self, rect: RectLimits) -> None:
        """Restore local grid limits after a temporary viewport change."""
        if self._local_rect is not None:
            self._local_rect = rect
            self._on_rect_change(None)

    def _effective_rect(self, shared_rect: RectLimits, local_rect: RectLimits | None) -> RectLimits:
        """Combine shared view coordinates and local coordinates for the active grid cell."""
        xlim, ylim = shared_rect[:2], shared_rect[2:]
        if local_rect is not None:
            if not self._shared[0]:
                xlim = local_rect[:2]
            if not self._shared[1]:
                ylim = local_rect[2:]
        for name, limits in (("x", xlim), ("y", ylim)):
            if self.axis_scale(name) is AxisScale.LOG:
                bounds = self._viewer._sanitize_log_extent(*limits, name, scale=AxisScale.LOG, layers=self._layers)
                if name == "x":
                    xlim = bounds
                else:
                    ylim = bounds
        return (*xlim, *ylim)

    @property
    def rect(self) -> tuple[float, float, float, float]:
        """Get rect"""
        rect = self.camera.rect
        return self._transform_rect(
            (rect.left, rect.right, rect.bottom, rect.top),
            inverse=True,
        )

    @rect.setter
    def rect(self, rect: Rect | ty.Iterable[float]) -> None:
        if self.rect == rect:
            return
        self._update_rect(rect)
        self._sync_to_model()

    def _on_sync_rect(self, event: ty.Any) -> None:
        """Sync rect from the Camera object to the Camera model when this camera was changed."""
        if self._initializing or self._applying or self.rect == self._synced_rect:
            return
        self._sync_to_model()

    def _sync_to_model(self) -> None:
        """Write the rect of this camera to the Camera model."""
        self._synced_rect = self.rect
        if self._local_rect is not None:
            self._local_rect = self._synced_rect
        xlim, ylim = self._camera.rect[:2], self._camera.rect[2:]
        if self._shared[0]:
            xlim = self._synced_rect[:2]
        if self._shared[1]:
            ylim = self._synced_rect[2:]
        with self._camera.events.rect.blocker(self._on_rect_change):
            self._camera.rect = (*xlim, *ylim)
        # the shared range of a marginal changed (e.g. it was panned), so its value axis follows the visible data
        if self._joint_autoscale and not self._autoscaling:
            self._autoscaling = True
            try:
                self._on_rect_change(None)
            finally:
                self._autoscaling = False

    def _update_rect(self, rect: Rect | ty.Iterable[float]) -> None:
        display_rect = self._transform_rect(rect, inverse=False)
        rect_obj = Rect(self.camera.rect)
        rect_obj.left, rect_obj.right, rect_obj.bottom, rect_obj.top = display_rect
        previous = self.rect
        self._applying = True
        try:
            self.camera._set_rect(rect_obj, interactive=False)
        finally:
            self._applying = False
        self._synced_rect = self.rect
        # the camera can limit the rect, so the model gets the rect that is shown when it changed
        # A local logarithmic axis can clip the shared linear range for this cell alone.
        if (
            self._synced_rect != previous
            and not np.allclose(self._synced_rect, rect, rtol=1e-10, atol=1e-10)
            and all(self.axis_scale(name) is getattr(self._viewer.axis, f"{name}_scale") for name in ("x", "y"))
        ):
            self._sync_to_model()

    @property
    def extent(self):
        """Get rect"""
        extent = self.camera._extent
        if extent is None:
            return None
        return self._transform_rect(
            (extent.left, extent.right, extent.bottom, extent.top),
            inverse=True,
        )

    @extent.setter
    def extent(self, extent):
        if self.extent == extent:
            return
        self.camera.extent = self._transform_rect(extent, inverse=False)

    def _on_aspect_change(self):
        self.camera.aspect = (
            None if self._viewer.canvas.grid.enabled and self._viewer.canvas.grid.joint else self._camera.aspect
        )

    def _on_mouse_toggles_change(self):
        self.mouse_pan = self._camera.mouse_pan
        self.camera.mouse_pan = self._camera.mouse_pan
        self.mouse_zoom = self._camera.mouse_zoom
        self.camera.mouse_zoom = self._camera.mouse_zoom

    def _on_zoom_change(self):
        if id(self._camera) in self._publishing_zoom:
            return
        self.zoom = self._camera.zoom

    def _on_rect_change(self, event):
        rect = self._autoscale_rect(self._effective_rect(self._camera.rect, self._local_rect))
        if self.rect != rect:
            self._update_rect(rect)

    def _on_force_rect_change(self, event):
        self._update_rect(self._autoscale_rect(self._effective_rect(self._camera.rect, self._local_rect)))

    def _on_extent_change(self, event):
        self.extent = self._effective_rect(self._camera.get_effective_extent(), self._local_extent)
        self._on_rect_change(None)

    def _on_range_change(self, event):
        self._on_extent_change(None)
        self.camera.reset_view()

    def _on_axis_mode_change(self, event):
        self.camera.axis_mode = self._camera.axis_mode

    def _on_extent_mode_change(self, event):
        self.camera.extent_mode = self._camera.extent_mode
        self._on_extent_change(None)
        self.camera.reset_view()

    def on_draw(self, event):
        """Called whenever the canvas is drawn. Update camera model rect."""
        if self.rect != self._synced_rect:
            self._sync_to_model()
        if self._viewer.canvas.grid.joint and not all(self._shared):
            return
        self._publishing_zoom.add(id(self._camera))
        try:
            self._camera.zoom = self.zoom
        finally:
            self._publishing_zoom.discard(id(self._camera))


def viewbox_key_event(event):
    """ViewBox key event handler.

    Parameters
    ----------
    event : vispy.util.event.Event
        The vispy event that triggered this method.
    """
    return


MouseToggledLimitedPanZoomCamera = add_mouse_pan_zoom_toggles(LimitedPanZoomCamera)
