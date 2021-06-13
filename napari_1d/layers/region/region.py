"""Infinite region"""
from typing import Tuple

import numpy as np
from napari.layers import Layer
from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.events import Event

# Local imports
from ._region_constants import Mode, Orientation
from ._region_mouse_bindings import move, select


class Region(Layer):
    """Line layer"""

    def __init__(
        self,
        data,
        *,
        label="",
        color=(1.0, 1.0, 0.0, 1.0),
        orientation="vertical",
        # base parameters
        name=None,
        metadata=None,
        scale=None,
        translate=None,
        rotate=None,
        shear=None,
        affine=None,
        opacity=1.0,
        blending="translucent",
        visible=True,
    ):
        # sanitize data
        if data is None:
            raise ValueError("Cannot instantiate layer without data")
        else:
            data = np.asarray(data)
        ndim = 2
        super().__init__(
            data,
            ndim,
            name=name,
            metadata=metadata,
            scale=scale,
            translate=translate,
            rotate=rotate,
            shear=shear,
            affine=affine,
            opacity=opacity,
            blending=blending,
            visible=visible,
        )
        self._data: np.ndarray = data
        self._color: np.ndarray = transform_color(color)[0]
        self._label = label
        self._orientation = Orientation(orientation)
        self._mode = Mode.PAN_ZOOM

        self.events.add(color=Event, label=Event, mode=Event, shifted=Event, accept=Event)
        self.visible = visible

    def accept(self):
        """Emit accept event"""
        self.events.accept()

    @property
    def mode(self) -> str:
        """str: Interactive mode

        Interactive mode. The normal, default mode is PAN_ZOOM, which
        allows for normal interactivity with the canvas.

        In MOVE the region is moved to new location
        """
        return str(self._mode)

    @mode.setter
    def mode(self, mode):
        mode = Mode(mode)

        if not self.editable:
            mode = Mode.PAN_ZOOM

        if mode == self._mode:
            return
        old_mode = self._mode

        if old_mode == Mode.SELECT:
            self.mouse_drag_callbacks.remove(select)
        elif old_mode == Mode.MOVE:
            self.mouse_drag_callbacks.remove(move)

        if mode == Mode.SELECT:
            self.cursor = "pointing"
            self.interactive = False
            self.help = "hold <space> to pan/zoom"
            self.mouse_drag_callbacks.append(select)
        elif mode == Mode.MOVE:
            self.cursor = "pointing"
            self.interactive = False
            self.help = "hold <space> to pan/zoom"
            self.mouse_drag_callbacks.append(move)
        elif mode == Mode.PAN_ZOOM:
            self.cursor = "standard"
            self.interactive = True
            self.help = ""
        else:
            raise ValueError("Mode not recognized")

        self._mode = mode
        self._set_highlight()
        self.events.mode(mode=mode)

    def move(
        self,
        start_coords: Tuple[float],
        end_coords: Tuple[float],
        finished: bool = False,
    ):
        """Move region to new location"""
        if self.is_vertical:
            start, end = start_coords[1], end_coords[1]
        else:
            start, end = start_coords[0], end_coords[0]
        self.data = np.asarray([start, end])
        if finished:
            self.events.shifted()

    @property
    def is_vertical(self) -> bool:
        """Flag to indicate whether this is a vertical region"""
        return self.orientation == "vertical"

    def _get_ndim(self):
        """Determine number of dimensions of the layer"""
        return 2

    def _get_state(self):
        """Get dictionary of layer state"""
        state = self._get_base_state()
        state.update({"data": self.data, "color": self.color, "label": self.label})
        return state

    def _update_thumbnail(self):
        """Update thumbnail with current data"""
        colormapped = np.zeros(self._thumbnail_shape)
        colormapped[..., 3] = 1
        # TODO: add magic here
        if self.orientation == Orientation.VERTICAL:
            y = colormapped.shape[0]
            colormapped[y + 10 : y - 10] = (1.0, 1.0, 1.0, 1.0)
        if self.orientation == Orientation.HORIZONTAL:
            y = colormapped.shape[1]
            colormapped[:, y + 10 : y - 10] = (1.0, 1.0, 1.0, 1.0)
        colormapped[..., 3] *= self.opacity
        self.thumbnail = colormapped

    @property
    def _view_data(self) -> np.ndarray:
        """Get the coords of the points in view

        Returns
        -------
        view_data : (N x D) np.ndarray
            Array of coordinates for the N points in view
        """
        return self.data

    @property
    def data(self):
        """Return data"""
        return self._data

    @data.setter
    def data(self, value: np.ndarray):
        self._data = value

        self._update_dims()
        self.events.data(value=self.data)
        self._set_editable()

    @property
    def orientation(self):
        """Orientation of the infinite region"""
        return self._orientation

    @property
    def color(self):
        """Get color"""
        return self._color

    @color.setter
    def color(self, value):
        self._color = transform_color(value)[0]
        self.events.color()

    @property
    def label(self):
        """Get label"""
        return self._label

    @label.setter
    def label(self, value):
        self._label = value
        self.events.label()

    def _set_view_slice(self):
        pass

    def _get_value(self, position):
        """Value of the data at a position in data coordinates"""
        return None

    @property
    def _extent_data(self) -> np.ndarray:
        if len(self.data) == 0:
            extrema = np.full((2, self.ndim), np.nan)
        else:
            mins, maxs = [0], [0]
            _mins = np.min(self.data)
            _maxs = np.max(self.data)
            if self.is_vertical:
                mins.append(_mins)
                maxs.append(_maxs)
            else:
                mins.insert(0, _mins)
                maxs.insert(0, _maxs)
            extrema = np.vstack([mins, maxs])
        return extrema
