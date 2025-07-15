"""Tool model."""

import typing as ty

import numpy as np
from napari._pydantic_compat import PrivateAttr
from napari.utils.compat import StrEnum
from napari.utils.events import EventedModel
from napari.utils.events.custom_types import Array

from napari_plot.components.tools import BaseTool, BoxTool, PolygonTool


class DragMode(StrEnum):
    """Interaction mode.

    No interaction tools:
        NONE : No interaction is possible

    Zoom-in tools:
        AUTO : swap between box and span depending on the modifier keys
        VERTICAL_SPAN : infinite region between two values in the vertical domain
        HORIZONTAL_SPAN : infinite region between two values in the horizontal domain
        BOX : rectangular box

        The `VERTICAL_SPAN`, `HORIZONTAL_SPAN` and `BOX` support additional actions which take advantage of the modifier
        keys such as `alt`, `control` and `shift`.

    Select tools:
        LASSO : lasso tool allowing selection of data points
        POLYGON : polygon tool allowing selection of data points
    """

    NONE = "none"
    # Zoom-tools
    AUTO = "auto"
    AUTO_TRIGGER = "auto_trigger"  # zoom + trigger
    VERTICAL_SPAN = "v_span"
    HORIZONTAL_SPAN = "h_span"
    BOX = "box"  # default interaction
    # Select-tools
    BOX_SELECT = "box_select"
    LASSO = "lasso"
    POLYGON = "polygon"


# List of `modes` which utilize the `BoxTool` model
BOX_ZOOM_TOOLS = [DragMode.AUTO, DragMode.AUTO_TRIGGER, DragMode.BOX, DragMode.VERTICAL_SPAN, DragMode.HORIZONTAL_SPAN]
POLYGON_TOOLS = [DragMode.POLYGON, DragMode.LASSO]
BOX_SELECT_TOOLS = [DragMode.BOX_SELECT]
SELECT_TOOLS = [DragMode.POLYGON, DragMode.LASSO, DragMode.BOX_SELECT]


class DragTool(EventedModel):
    """Tool model.

    Attributes
    ----------
    active : DragMode
        Mode used to determine which tool should be used for interaction.
    tool : BaseTool
        Tool which should be used for interaction.
    shift : ty.Tuple
        Tuple containing last x/y-axis range while `shift` key was held down.
    alt : ty.Tuple
        Tuple containing last x/y-axis range while `alt` key was held down.
    ctrl: ty.Tuple
        Tuple containing last x/y-axis range while `ctrl` key was held down.

    The `shift`, `alt` and `ctrl` attributes hold values in order: `xmin, xmax, ymin, ymax`.

    """

    active: DragMode = DragMode.NONE
    tool: ty.Optional[BaseTool] = None
    selection_active: bool = False

    vertices: Array[float, (-1, 2)] = np.zeros((0, 2), dtype=float)
    shift: Array[float, (4,)] = (0, 0, 0, 0)
    alt: Array[float, (4,)] = (0, 0, 0, 0)
    ctrl: Array[float, (4,)] = (0, 0, 0, 0)

    # instances of the the tools that are kept around - these are not evented
    _box = PrivateAttr(default_factory=BoxTool)
    _polygon = PrivateAttr(default_factory=PolygonTool)

    @property
    def selecting(self) -> bool:
        """Flag to indicate whether the current tool is considered a `selecting` tool."""
        return (
            self.active
            in [
                DragMode.BOX,
                DragMode.VERTICAL_SPAN,
                DragMode.HORIZONTAL_SPAN,
            ]
            or self.selection_active
        )

    @property
    def modifiers_active(self) -> bool:
        """Flag to indicate whether any of the modifier keys are selected."""
        return self.shift_active or self.alt_active or self.ctrl_active

    @property
    def shift_active(self) -> bool:
        """Shift active."""
        return not all(v == 0 for v in self.shift)

    @property
    def alt_active(self) -> bool:
        """Alt active."""
        return not all(v == 0 for v in self.alt)

    @property
    def ctrl_active(self) -> bool:
        """Ctrl active."""
        return not all(v == 0 for v in self.ctrl)
