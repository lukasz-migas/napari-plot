"""Infinite region"""
from typing import Tuple

import numpy as np
from napari.layers.base import Layer, no_op
from napari.layers.utils.color_manager import ColorManager
from napari.utils.events import Event

from ._infline_constants import Mode, Orientation
from ._infline_mouse_bindings import add, highlight, move, select


class InfLine(Layer):
    """InfLine layer"""

    # The max length of the line that will ever be used to render the thumbnail
    # If more points are present, they will be sub-sampled
    _max_line_thumbnail = 1024

    def __init__(
        self,
        data,
        orientations,
        *,
        label="",
        color="red",
        width=1,
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
            data = np.asarray([])
        else:
            data = np.asarray(data)

        if not len(data) == len(orientations):
            raise ValueError("The number of points and orientations is incorrect. They must be matched.")

        super().__init__(
            data,
            ndim=2,
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
        self._data = data
        self._color = ColorManager._from_layer_kwargs(n_colors=len(data), colors=color, properties={})
        self._label = label
        self._orientations = [Orientation(orientation) for orientation in orientations]
        self._width = width
        self._mode = Mode.PAN_ZOOM

        # indices of selected lines
        self._selected_data = set()
        self._selected_data_stored = set()

        self.events.add(color=Event, width=Event, label=Event, mode=Event, shifted=Event)
        self.visible = visible

    @property
    def mode(self) -> str:
        """str: Interactive mode

        Interactive mode. The normal, default mode is PAN_ZOOM, which
        allows for normal interactivity with the canvas.

        In MOVE the region is moved to new location
        """
        return str(self._mode)

    _drag_modes = {Mode.ADD: add, Mode.SELECT: select, Mode.PAN_ZOOM: no_op, Mode.MOVE: move}
    _move_modes = {Mode.ADD: no_op, Mode.SELECT: highlight, Mode.PAN_ZOOM: no_op}
    _cursor_modes = {Mode.ADD: "pointing", Mode.SELECT: "standard", Mode.PAN_ZOOM: "standard"}

    @mode.setter
    def mode(self, mode):
        mode, changed = self._mode_setter_helper(mode, Mode)
        if not changed:
            return

        assert mode is not None, mode
        old_mod = self._mode

        if mode == Mode.ADD:
            self.selected_data = set()
            self.interactive = False

        if mode == Mode.PAN_ZOOM:
            self.help = ""
            self.interactive = True
        else:
            self.help = "Hold <space> to pan/zoom."

        if mode != Mode.SELECT or old_mod != Mode.SELECT:
            self._selected_data_stored = set()

        self._mode = mode
        self._set_highlight()
        self.events.mode(mode=mode)

    @property
    def selected_data(self) -> set:
        """set: set of currently selected points."""
        return self._selected_data

    @selected_data.setter
    def selected_data(self, selected_data):
        pass

    def add(self, pos, orientation):
        """Adds point at coordinate.

        Parameters
        ----------
        pos : sequence
            Sequence of values to add infinite lines at
        orientation : sequence
            Sequence of orientations
        """
        assert len(pos) == len(orientation)
        self._orientations.extend(orientation)
        self.data = np.append(self.data, np.asarray(pos), axis=0)

    def move(self, new_coords: Tuple[float], finished: bool = False):
        """Move region to new location"""
        # if self.is_vertical:
        #     pos = new_coords[1]
        # else:
        #     pos = new_coords[0]
        # self.data = np.asarray(pos)
        # if finished:
        #     self.events.shifted()

    def _get_ndim(self) -> int:
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
        # if self.orientation == Orientation.VERTICAL:
        #     y = colormapped.shape[0]
        #     colormapped[y + 10 : y - 10] = (1.0, 1.0, 1.0, 1.0)
        # if self.orientation == Orientation.HORIZONTAL:
        #     y = colormapped.shape[1]
        #     colormapped[:, y + 10 : y - 10] = (1.0, 1.0, 1.0, 1.0)
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
    def data(self, data: np.ndarray):
        current_n_points = len(self._data)
        self._data = data

        with self.events.blocker_all():
            with self._color.events.blocker_all():
                if len(data) < current_n_points:
                    # if there are fewer lines, remove the colors of the extra ones
                    self._color._remove(np.arange(len(data)), len(self._color.colors))
                elif len(data) > current_n_points:
                    # if there are now more points, add the colors of the new ones
                    adding = len(data) - current_n_points
                    self._color._add(n_colors=adding)

        self._update_dims()
        self.events.data(value=self.data)
        self._set_editable()

    @property
    def orientations(self):
        """Orientation of the infinite region."""
        return self._orientations

    @property
    def color(self) -> np.ndarray:
        """Get color"""
        return self._color.colors

    @color.setter
    def color(self, color):
        self._color._set_color(color=color, n_colors=len(self.data))
        self.events.color()

    @property
    def label(self):
        """Get label"""
        return self._label

    @label.setter
    def label(self, value):
        self._label = value
        self.events.label()

    @property
    def width(self):
        """Get width"""
        return self._width

    @width.setter
    def width(self, value: float):
        self._width = value
        self.events.width()

    def _set_view_slice(self):
        self.events.set_data()

    def _get_value(self, position):
        """Value of the data at a position in data coordinates"""
        return None

    @property
    def _extent_data(self) -> np.ndarray:
        return np.full((2, 2), np.nan)

    def _set_highlight(self, force=False):
        """Render highlights.

        Parameters
        ----------
        force : bool
            Bool that forces a redraw to occur when `True`.
        """
