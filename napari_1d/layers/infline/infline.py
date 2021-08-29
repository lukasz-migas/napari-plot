"""Infinite region"""
import numpy as np
from napari.layers.base import Layer, no_op
from napari.layers.utils.color_transformations import (
    normalize_and_broadcast_colors,
    transform_color,
    transform_color_with_defaults,
)
from napari.utils.events import Event

from ._infline_constants import Mode, Orientation
from ._infline_mouse_bindings import add, highlight, move, select
from ._infline_utils import extract_inf_line_orientation


class InfLine(Layer):
    """InfLine layer"""

    _drag_modes = {Mode.ADD: add, Mode.SELECT: select, Mode.PAN_ZOOM: no_op, Mode.MOVE: move}
    _move_modes = {Mode.ADD: no_op, Mode.SELECT: highlight, Mode.PAN_ZOOM: no_op, Mode.MOVE: no_op}
    _cursor_modes = {
        Mode.ADD: "standard",
        Mode.SELECT: "standard",
        Mode.PAN_ZOOM: "standard",
        Mode.MOVE: "cross",
    }

    def __init__(
        self,
        data,
        *,
        orientations="vertical",
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
            data, orientations = extract_inf_line_orientation(data, orientations)
            data = np.asarray(data, dtype=np.float64)

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
        self._label = label
        self._width = width
        self._data = data
        self._mode = Mode.PAN_ZOOM

        # each line can have its own color
        self._color = transform_color(color)  # np.asarray([transform_color(_color) for _color in color])
        # each line can be either horizontal or vertical
        self._orientations = [Orientation(orientation) for orientation in orientations]

        # set the current_* properties
        if len(data) > 0:
            self._current_color = self.color[-1]
        else:
            self._current_color = transform_color_with_defaults(
                num_entries=1,
                colors=color,
                elem_name="color",
                default="white",
            )

        # indices of selected lines
        self._value = None
        self._selected_data = set()
        self._selected_data_stored = set()
        self._selected_box = None

        self._drag_start = None
        self._drag_box = None
        self._drag_box_stored = None

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

    @mode.setter
    def mode(self, mode):
        mode, changed = self._mode_setter_helper(mode, Mode)
        if not changed:
            return

        assert mode is not None, mode
        old_mode = self._mode

        if mode == Mode.SELECT:
            self.selected_data = set()

        if mode == Mode.PAN_ZOOM:
            self.help = ""
        else:
            self.help = "Hold <space> to pan/zoom."

        if mode != Mode.SELECT or old_mode != Mode.SELECT:
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

    @property
    def current_color(self):
        """Get current color."""
        return self._current_color

    def add(self, pos, orientation):
        """Adds point at coordinate.

        Parameters
        ----------
        pos : sequence
            Sequence of values to add infinite lines at
        orientation : sequence
            Sequence of orientations
        """
        if len(pos) != len(orientation):
            raise ValueError(
                "When adding infinite lines, it is expected that that the number of values matches the number of"
                " orientations."
            )
        self._orientations.extend(orientation)
        self.data = np.append(self._data, np.asarray(pos))

    def move(self, index: int, new_pos: float, finished: bool = False):
        """Move region to new location"""
        if index > len(self.data):
            raise ValueError("Selected index is larger than total number of elements.")
        self._data[index] = new_pos
        self.data = self._data

        if finished:
            self.events.shifted()

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
        colormapped[14:18] = (1.0, 1.0, 1.0, 1.0)
        colormapped[:, 14:18] = (1.0, 1.0, 1.0, 1.0)
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
            if len(data) < current_n_points:
                # if there are fewer lines, remove the colors of the extra ones
                self._color = np.delete(self._color, np.arange(len(data)), len(self._color))
            elif len(data) > current_n_points:
                # if there are now more points, add the colors of the new ones
                adding = len(data) - current_n_points
                transformed_color = transform_color_with_defaults(
                    num_entries=adding,
                    colors=self._current_color,
                    elem_name="color",
                    default="white",
                )
                broadcasted_colors = normalize_and_broadcast_colors(adding, transformed_color)
                self._color = np.concatenate((self._color, broadcasted_colors))

        self._update_dims()
        self.events.data(value=self.data)
        self._set_editable()

    @property
    def orientations(self):
        """Orientations of the infinite lines."""
        return self._orientations

    @property
    def color(self) -> np.ndarray:
        """Get color"""
        return self._color

    @color.setter
    def color(self, color):
        if self.selected_data:
            print("update selected data")
        else:
            self._current_color = color
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
