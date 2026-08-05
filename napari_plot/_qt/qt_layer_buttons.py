"""Layer buttons"""

from __future__ import annotations

import typing as ty
from functools import partial

import numpy as np
import qtextra.helpers as hp
from napari.utils.action_manager import action_manager
from qtextra.widgets.qt_button_icon import QtImagePushButton
from qtpy.QtWidgets import QAction, QFrame, QMenu, QWidget


def _add_new_points(viewer):
    viewer.add_points(ndim=max(viewer.dims.ndim, 2), scale=viewer.layers.extent.step)


def _add_new_shapes(viewer):
    viewer.add_shapes(ndim=max(viewer.dims.ndim, 2), scale=viewer.layers.extent.step)


def _add_new_region(viewer):
    viewer.add_region(scale=viewer.layers.extent.step, opacity=0.75, name="Region")


def _add_new_inf_line(viewer):
    viewer.add_inf_line(scale=viewer.layers.extent.step, name="InfLine")


def _add_empty_layer(viewer, layer_name: str):
    """Add an empty layer of the requested built-in or napari-plot type."""
    scale = viewer.layers.extent.step
    factories = {
        "Points": lambda: viewer.add_points(ndim=max(viewer.dims.ndim, 2), scale=scale),
        "Shapes": lambda: viewer.add_shapes(ndim=max(viewer.dims.ndim, 2), scale=scale),
        "Line": lambda: viewer.add_line(np.empty((0, 2)), scale=scale, name="Line"),
        "Bar": lambda: viewer.add_bar(None, scale=scale, name="Bar"),
        "Scatter": lambda: viewer.add_scatter(None, scale=scale, name="Scatter"),
        "MultiLine": lambda: viewer.add_multi_line(None, scale=scale, name="MultiLine"),
        "Centroids": lambda: viewer.add_centroids(None, scale=scale, name="Centroids"),
        "Text": lambda: viewer.add_text(None, None, scale=scale, name="Text"),
        "Region": lambda: viewer.add_region(None, scale=scale, opacity=0.75, name="Region"),
        "InfLine": lambda: viewer.add_inf_line(None, scale=scale, name="InfLine"),
    }
    return factories[layer_name]()


def create_add_layer_menu(parent: QWidget, viewer) -> QMenu:
    """Create a menu containing every supported layer type."""
    menu = QMenu(parent)
    for layer_name in (
        "Line",
        "Bar",
        "Scatter",
        "MultiLine",
        "Centroids",
        "Text",
        "Region",
        "InfLine",
        "Points",
        "Shapes",
    ):
        action = QAction(f"Add {layer_name}", menu)
        action.triggered.connect(partial(_add_empty_layer, viewer, layer_name))
        menu.addAction(action)
    return menu


def make_qta_btn(
    parent: QWidget,
    icon_name: str,
    tooltip: str = "",
    action: str = "",
    extra_tooltip_text: str = "",
    **kwargs: ty.Any,
) -> QtImagePushButton:
    """Make a button with an icon from QtAwesome."""
    btn = hp.make_qta_btn(parent=parent, icon_name=icon_name, tooltip=tooltip, **kwargs)
    btn.set_qta_size_preset("normal")
    btn.setProperty("layer_button", True)
    if action:
        action_manager.bind_button(action, btn, extra_tooltip_text=extra_tooltip_text)
    return btn


class QtLayerButtons(QFrame):
    """Button controls for napari layers.

    Parameters
    ----------
    viewer : napari.components.ViewerModel
        Napari viewer containing the rendered scene, layers, and controls.

    Attributes
    ----------
    delete_btn : QtDeleteButton
        Button to delete selected layers.
    viewer : napari.components.ViewerModel
        Napari viewer containing the rendered scene, layers, and controls.
    """

    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer
        self.delete_btn = make_qta_btn(
            self,
            "delete",
            tooltip="Delete selected layers",
            func=self.viewer.layers.remove_selected,
            # action="napari:delete_selected_layers",  # TODO: change to napari_plot
        )
        self.delete_btn.setParent(self)

        self.add_layer_btn = make_qta_btn(
            self,
            "add",
            "Add layer",
            func=self._open_add_layer_menu,
        )

        self.new_points_btn = make_qta_btn(
            self,
            "new_points",
            "Add new points layer",
            func=partial(_add_new_points, self.viewer),
        )

        self.new_shapes_btn = make_qta_btn(
            self,
            "new_shapes",
            "Add new shapes layer",
            func=partial(_add_new_shapes, self.viewer),
        )

        layout = hp.make_h_layout(parent=self, spacing=2, margin=0)
        layout.addWidget(self.add_layer_btn)
        layout.addWidget(self.new_shapes_btn)
        layout.addWidget(self.new_points_btn)
        layout.addStretch(0)
        layout.addWidget(self.delete_btn)

    def _open_add_layer_menu(self) -> None:
        """Open the complete layer creation menu."""
        hp.show_menu(menu=create_add_layer_menu(self, self.viewer))


class QtViewerButtons(QFrame):
    """Button controls for the napari viewer.

    Parameters
    ----------
    viewer : napari.components.ViewerModel
        Napari viewer containing the rendered scene, layers, and controls.
    parent : QWidget
        parent of the widget

    Attributes
    ----------
    resetViewButton : QtViewerPushButton
        Button resetting the view of the rendered scene.
    viewer : napari.components.ViewerModel
        Napari viewer containing the rendered scene, layers, and controls.
    """

    def __init__(self, viewer, parent=None, **kwargs):
        super().__init__()

        self.viewer = viewer

        self.resetViewButton = make_qta_btn(
            self,
            "home",
            "Reset view",
            func=self.viewer.reset_view,
            # action="napari:reset_view",
        )

        # only add console if its QtViewer
        self.consoleButton = None
        if kwargs.get("dock_console", False):
            self.consoleButton = make_qta_btn(
                self,
                "ipython",
                "Show/hide console panel",
                func=parent.on_toggle_console_visibility,
            )

        layout = hp.make_h_layout(parent=self, spacing=2, margin=0)
        if self.consoleButton is not None:
            layout.addWidget(self.consoleButton)
        layout.addWidget(self.resetViewButton)
        layout.addStretch(0)
