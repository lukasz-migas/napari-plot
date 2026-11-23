"""Joint plot layout using the viewer's layer list."""

from __future__ import annotations

from math import isfinite
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from napari.layers import Layer

    from napari_plot.components.viewer_model import ViewerModel

JOINT_PANEL_KEY = "_napari_plot_joint_panel"
JointPanel = Literal["joint", "top", "right"]


def joint_panel(layer: Layer, *, top: bool, right: bool) -> str:
    """Return a layer's available panel, falling back to the joint panel."""
    panel = layer.metadata.get(JOINT_PANEL_KEY, "joint")
    return (
        panel
        if isinstance(panel, str)
        and panel in ("joint", "top", "right")
        and (panel != "top" or top)
        and (panel != "right" or right)
        else "joint"
    )


class JointGrid:
    """Arrange a main plot and optional top and right marginals on one viewer.

    ``ratio`` controls the size of the main panel relative to the marginals.
    The top shares the main x axis and the right shares the main y axis.
    """

    def __init__(self, viewer: ViewerModel, *, top: bool = True, right: bool = True, ratio: float = 5) -> None:
        if not top and not right:
            raise ValueError("At least one marginal panel is required.")
        if not isfinite(ratio) or ratio <= 0:
            raise ValueError("ratio must be positive.")
        self.viewer = viewer
        self.layers: list[Layer] = []
        grid = viewer.canvas.grid
        grid.joint_top, grid.joint_right, grid.joint_ratio = top, right, ratio
        grid.joint = True
        grid.enabled = True
        if not viewer.layers:
            viewer.reset_view()

    def _validate_panel(self, panel: JointPanel) -> None:
        grid = self.viewer.canvas.grid
        if (
            panel not in ("joint", "top", "right")
            or (panel == "top" and not grid.joint_top)
            or (panel == "right" and not grid.joint_right)
        ):
            raise ValueError(f"Panel {panel!r} is not available.")

    def add_layer(self, layer: Layer, *, panel: JointPanel = "joint") -> Layer:
        """Add or move a layer to a panel and return it."""
        self._validate_panel(panel)
        layer.metadata = {**layer.metadata, JOINT_PANEL_KEY: panel}
        if layer not in self.viewer.layers:
            self.viewer.add_layer(layer)
        if layer not in self.layers:
            self.layers.append(layer)
        return layer

    def set_axis_labels(
        self,
        x_var: str | None = None,
        y_var: str | None = None,
        *,
        panel: JointPanel = "joint",
        visible: bool | None = None,
    ) -> JointGrid:
        """Set one panel's axis labels and optionally hide or show them.

        Use ``y_var`` for the top margin and ``x_var`` for the right margin.
        Toggling ``visible`` preserves the label text, ticks, and axis lines.
        """
        self._validate_panel(panel)
        grid = self.viewer.canvas.grid
        if panel == "top":
            if x_var is not None:
                raise ValueError("Set the shared x label on the joint panel.")
            if y_var is not None:
                grid.joint_top_label = y_var
        elif panel == "right":
            if y_var is not None:
                raise ValueError("Set the shared y label on the joint panel.")
            if x_var is not None:
                grid.joint_right_label = x_var
        else:
            if x_var is not None:
                self.viewer.axis.x_label = x_var
            if y_var is not None:
                self.viewer.axis.y_label = y_var

        hidden = grid.joint_hidden_labels
        if visible is False and panel not in hidden:
            grid.joint_hidden_labels = (*hidden, panel)
        elif visible is True and panel in hidden:
            grid.joint_hidden_labels = tuple(name for name in hidden if name != panel)
        return self
