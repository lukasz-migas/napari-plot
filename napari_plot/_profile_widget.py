"""Profile widgets that plot napari image values: along Shapes lines, or along an axis under the cursor."""

from __future__ import annotations

import typing as ty
from contextlib import suppress

import numpy as np
import qtextra.helpers as hp
from napari.layers import Image, Shapes
from qtpy.QtWidgets import QLayout

from napari_plot._layer_sampling import (
    image_plane,
    layer_axes,
    layer_color,
    resample_path,
    sample_bilinear,
    world_to_layer,
)
from napari_plot._plot_widget import NapariPlotWidget

if ty.TYPE_CHECKING:
    import napari

    from napari_plot.layers import Line

__all__ = ["CursorProfileWidget", "LineProfileWidget"]


class HostPlotWidget(NapariPlotWidget):
    """Plot widget that keeps one line per data series drawn from a napari viewer.

    Subclasses build a ``{name: (xy, color)}`` mapping and pass it to ``set_series``, which reuses, updates and
    removes plot layers so the plot always matches the mapping.
    """

    def __init__(self, napari_viewer: napari.viewer.Viewer) -> None:
        super().__init__(napari_viewer)
        self._series: dict[str, Line] = {}
        self._connections: list[tuple[ty.Any, ty.Callable]] = []

    def add_controls(self, layout: QLayout) -> None:
        """Place a row of controls above the plot."""
        self.layout().insertLayout(0, layout)

    def connect_host(self, emitter: ty.Any, callback: ty.Callable) -> None:
        """Connect to a host event and disconnect it when the widget closes."""
        hp.connect(emitter, callback, state=True)
        self._connections.append((emitter, callback))

    def disconnect_host(self, emitter: ty.Any | None = None) -> None:
        """Disconnect host events, either all of them or those of one emitter."""
        keep = []
        for connected, callback in self._connections:
            if emitter is None or connected is emitter:
                with suppress(TypeError, ValueError, RuntimeError):
                    hp.connect(connected, callback, state=False)
            else:
                keep.append((connected, callback))
        self._connections = keep

    def set_series(self, series: dict[str, tuple[np.ndarray, ty.Any]]) -> None:
        """Show exactly the given lines, keyed by layer name.

        Parameters
        ----------
        series : dict
            Maps a series name to ``(xy, color)``, where ``xy`` is an (N, 2) array of x and y values.
            Rows with non-finite values are dropped. Adding lines keeps the active plot layer active.
        """
        active = self.viewer_plot.layers.selection.active
        for name in list(self._series):
            layer = self._series[name]
            if name not in series or layer not in self.viewer_plot.layers:
                if layer in self.viewer_plot.layers:
                    self.viewer_plot.layers.remove(layer)
                del self._series[name]
        for name, (xy, color) in series.items():
            xy = np.asarray(xy, dtype=float).reshape(-1, 2)
            xy = xy[np.isfinite(xy).all(axis=1)]
            if name in self._series:
                layer = self._series[name]
                layer.data = xy
                layer.color = color
            else:
                self._series[name] = self.viewer_plot.add_line(xy, color=color, name=name)
        if active is not None and active in self.viewer_plot.layers:
            self.viewer_plot.layers.selection.active = active

    def target_images(self) -> list[Image]:
        """Return the selected image layers, or every visible image layer when none is selected."""
        selected = [
            layer for layer in self.viewer.layers if isinstance(layer, Image) and layer in self.viewer.layers.selection
        ]
        if selected:
            return selected
        return [layer for layer in self.viewer.layers if isinstance(layer, Image) and layer.visible]

    def closeEvent(self, event: ty.Any) -> None:
        """Disconnect host events before closing."""
        self.disconnect_host()
        super().closeEvent(event)


class LineProfileWidget(HostPlotWidget):
    """Plot image intensities along the line and path shapes of a Shapes layer.

    The widget follows the most recently selected Shapes layer and samples the selected image layers (or all
    visible images) on the currently displayed plane, with bilinear interpolation at about one sample per pixel.
    The x-axis is the distance along each shape in world units.
    """

    def __init__(self, napari_viewer: napari.viewer.Viewer) -> None:
        super().__init__(napari_viewer)
        self.shapes_layer: Shapes | None = None
        self.viewer_plot.axis.x_label = "Distance"
        self.viewer_plot.axis.y_label = "Intensity"

        self.connect_host(self.viewer.layers.selection.events.active, self._on_active_layer)
        self.connect_host(self.viewer.layers.selection.events.changed, self.update_profiles)
        self.connect_host(self.viewer.layers.events.inserted, self._on_layers_changed)
        self.connect_host(self.viewer.layers.events.removed, self._on_layers_changed)
        self.connect_host(self.viewer.dims.events.current_step, self.update_profiles)
        self.connect_host(self.viewer.dims.events.order, self.update_profiles)
        self._on_layers_changed()

    def set_shapes_layer(self, layer: Shapes | None) -> None:
        """Profile along the line and path shapes of ``layer``."""
        if self.shapes_layer is not None:
            self.disconnect_host(self.shapes_layer.events.set_data)
            self.disconnect_host(self.shapes_layer.events.data)
        self.shapes_layer = layer
        if layer is not None:
            self.connect_host(layer.events.set_data, self.update_profiles)
            self.connect_host(layer.events.data, self.update_profiles)
        self.update_profiles()

    def _on_active_layer(self, event: ty.Any = None) -> None:
        if isinstance(self.viewer.layers.selection.active, Shapes):
            self.set_shapes_layer(self.viewer.layers.selection.active)

    def _on_layers_changed(self, event: ty.Any = None) -> None:
        shapes = [layer for layer in self.viewer.layers if isinstance(layer, Shapes)]
        if isinstance(self.viewer.layers.selection.active, Shapes):
            self.set_shapes_layer(self.viewer.layers.selection.active)
        elif self.shapes_layer not in shapes:
            self.set_shapes_layer(shapes[-1] if shapes else None)
        else:
            self.update_profiles()
        for image in (layer for layer in self.viewer.layers if isinstance(layer, Image)):
            self.disconnect_host(image.events.data)
            self.connect_host(image.events.data, self.update_profiles)

    def _paths(self) -> list[tuple[int, np.ndarray]]:
        """Return (shape index, world-coordinate vertices) for each line or path shape."""
        layer = self.shapes_layer
        if layer is None:
            return []
        paths = []
        base = np.asarray(self.viewer.dims.point, dtype=float)
        for index, (vertices, shape_type) in enumerate(zip(layer.data, layer.shape_type, strict=False)):
            if shape_type not in ("line", "path") or len(vertices) < 2:
                continue
            world = np.tile(base, (len(vertices), 1))
            world[:, -layer.ndim :] = layer._data_to_world(np.asarray(vertices, dtype=float))
            paths.append((index, world))
        return paths

    def profiles(self) -> dict[str, tuple[np.ndarray, ty.Any]]:
        """Compute one profile per (image, shape) pair as ``{name: (xy, color)}``."""
        series: dict[str, tuple[np.ndarray, ty.Any]] = {}
        paths = self._paths()
        if not paths:
            return series
        displayed = sorted(self.viewer.dims.displayed)
        for image_index, image in enumerate(self.target_images()):
            try:
                plane, plane_axes = image_plane(image, self.viewer.dims)
            except ValueError:
                continue
            if layer_axes(image, self.viewer.dims, displayed) != plane_axes or len(plane_axes) != 2:
                continue
            step = float(np.min(np.abs(np.asarray(image.scale)[plane_axes])))
            for shape_index, world in paths:
                points, distance = resample_path(world[:, displayed], step=step)
                samples = np.tile(world[0], (len(points), 1))
                samples[:, displayed] = points
                coords = world_to_layer(image, samples)[:, plane_axes]
                values = sample_bilinear(plane, coords)
                name = f"{image.name} | shape {shape_index}"
                series[name] = (np.column_stack((distance, values)), layer_color(image, image_index))
        return series

    def update_profiles(self, event: ty.Any = None) -> None:
        """Recompute and redraw all profiles."""
        series = self.profiles()
        self.set_series(series)
        if self.shapes_layer is None:
            self.viewer_plot.text_overlay.text = "Add a Shapes layer and draw a line or path"
        elif not series:
            self.viewer_plot.text_overlay.text = f"Draw a line or path in '{self.shapes_layer.name}'"
        else:
            self.viewer_plot.text_overlay.text = ""


class CursorProfileWidget(HostPlotWidget):
    """Plot image values along one axis (e.g. z or time) at the pixel under the cursor.

    The widget samples the selected image layers (or all visible images). Choose the axis among the dimensions
    that are not displayed; a vertical line marks the current position of that axis.
    """

    def __init__(self, napari_viewer: napari.viewer.Viewer) -> None:
        super().__init__(napari_viewer)
        self.axis_choice = hp.make_combobox(
            self, tooltip="Axis to plot the profile along", func_index=self._on_axis_changed
        )
        self.add_controls(hp.make_form_layout(("Profile axis", self.axis_choice), margin=(6, 6, 6, 0)))
        self.viewer_plot.axis.y_label = "Intensity"
        self.marker = self.viewer_plot.axvline(0, color="#d62728", name="Current step")

        self.connect_host(self.viewer.cursor.events.position, self.update_profiles)
        self.connect_host(self.viewer.layers.selection.events.changed, self.update_profiles)
        self.connect_host(self.viewer.dims.events.current_step, self._update_marker)
        self.connect_host(self.viewer.dims.events.ndim, self._update_axes)
        self.connect_host(self.viewer.dims.events.order, self._update_axes)
        self.connect_host(self.viewer.dims.events.ndisplay, self._update_axes)
        self.connect_host(self.viewer.dims.events.axis_labels, self._update_axes)
        self._update_axes()

    @property
    def axis(self) -> int | None:
        """World axis the profile runs along, or None when every axis is displayed."""
        data = self.axis_choice.currentData()
        return None if data is None else int(data)

    @axis.setter
    def axis(self, axis: int) -> None:
        hp.set_combobox_current_index(self.axis_choice, axis)

    def _axis_label(self, axis: int) -> str:
        """Return the axis label, or 'Axis N' for napari's default numeric labels."""
        label = str(self.viewer.dims.axis_labels[axis])
        return f"Axis {axis}" if label.lstrip("-").isdigit() else label

    def _update_axes(self, event: ty.Any = None) -> None:
        dims = self.viewer.dims
        axes = [axis for axis in range(dims.ndim) if axis not in dims.displayed]
        current = self.axis
        with hp.qt_signals_blocked(self.axis_choice):
            self.axis_choice.clear()
            for axis in axes:
                self.axis_choice.addItem(self._axis_label(axis), axis)
            if current in axes:
                hp.set_combobox_current_index(self.axis_choice, current)
        self._on_axis_changed()

    def _on_axis_changed(self, _index: int | None = None) -> None:
        axis = self.axis
        self.viewer_plot.axis.x_label = "" if axis is None else self._axis_label(axis)
        self._update_marker()
        self.update_profiles()

    def _update_marker(self, event: ty.Any = None) -> None:
        axis = self.axis
        self.marker.visible = axis is not None
        if axis is not None:
            self.marker.data = [float(self.viewer.dims.point[axis])]

    def profiles(self) -> dict[str, tuple[np.ndarray, ty.Any]]:
        """Compute one profile per image at the cursor as ``{name: (xy, color)}``."""
        series: dict[str, tuple[np.ndarray, ty.Any]] = {}
        axis = self.axis
        if axis is None:
            return series
        position = np.asarray(self.viewer.cursor.position, dtype=float)
        if len(position) != self.viewer.dims.ndim:
            return series
        for image_index, image in enumerate(self.target_images()):
            layer_axis = layer_axes(image, self.viewer.dims, [axis])
            if not layer_axis or image.multiscale:
                continue
            coords = world_to_layer(image, position)[0]
            index: list[int | slice] = []
            for current, size in enumerate(image.data.shape[: image.ndim]):
                if current == layer_axis[0]:
                    index.append(slice(None))
                    continue
                value = int(np.round(coords[current]))
                if not 0 <= value < size:
                    break
                index.append(value)
            else:
                values = np.asarray(image.data[tuple(index)], dtype=float)
                if image.rgb:
                    values = values[..., :3].mean(axis=-1)
                origin = np.zeros((len(values), image.ndim))
                origin[:, layer_axis[0]] = np.arange(len(values))
                world = image._data_to_world(origin)[:, layer_axis[0]]
                series[image.name] = (np.column_stack((world, values)), layer_color(image, image_index))
        return series

    def update_profiles(self, event: ty.Any = None) -> None:
        """Recompute and redraw the profiles under the cursor."""
        series = self.profiles()
        self.set_series(series)
        if self.axis is None:
            self.viewer_plot.text_overlay.text = "Needs a dimension that is not displayed (e.g. z or time)"
        elif not series:
            self.viewer_plot.text_overlay.text = "Move the cursor over an image"
        else:
            self.viewer_plot.text_overlay.text = ""
