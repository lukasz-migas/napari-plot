"""Tool model."""
import typing as ty
from enum import Enum

from napari.utils.events import EventedModel
from napari.utils.events.custom_types import Array

from .tools import BaseTool


class DragMode(str, Enum):
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
    AUTO = "auto"
    VERTICAL_SPAN = "v_span"
    HORIZONTAL_SPAN = "h_span"
    BOX = "box"  # default interaction
    LASSO = "lasso"  # TODO
    POLYGON = "polygon"  # TODO


# List of `modes` which utilize the `BoxTool` model
BOX_INTERACTIVE_TOOL = [
    DragMode.AUTO,
    DragMode.BOX,
    DragMode.VERTICAL_SPAN,
    DragMode.HORIZONTAL_SPAN,
]


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

    shift: Array[float, (4,)] = 0, 0, 0, 0
    alt: Array[float, (4,)] = 0, 0, 0, 0
    ctrl: Array[float, (4,)] = 0, 0, 0, 0

    @property
    def selecting(self) -> bool:
        """Flag to indicate whether the current tool is considered a `selecting` tool."""
        return self.active in [
            DragMode.BOX,
            DragMode.VERTICAL_SPAN,
            DragMode.HORIZONTAL_SPAN,
        ]
