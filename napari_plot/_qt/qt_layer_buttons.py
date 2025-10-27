"""Layer buttons"""

from __future__ import annotations

import typing as ty
from functools import partial

import qtextra.helpers as hp
from napari.utils.action_manager import action_manager
from qtextra.widgets.qt_button_icon import QtImagePushButton
from qtpy.QtWidgets import QFrame, QWidget


def _add_new_points(viewer):
    viewer.add_points(ndim=max(viewer.dims.ndim, 2), scale=viewer.layers.extent.step)


def _add_new_shapes(viewer):
    viewer.add_shapes(ndim=max(viewer.dims.ndim, 2), scale=viewer.layers.extent.step)


def _add_new_region(viewer):
    viewer.add_region(scale=viewer.layers.extent.step, opacity=0.75, name="Region")


def _add_new_inf_line(viewer):
    viewer.add_inf_line(scale=viewer.layers.extent.step, name="InfLine")


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
    btn.set_normal()
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
            action="napari:delete_selected_layers",  # TODO: change to napari_plot
        )
        self.delete_btn.setParent(self)

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

        self.new_region_btn = make_qta_btn(
            self,
            "new_region",
            "Add new region layer",
            func=partial(_add_new_region, self.viewer),
        )

        self.new_infline_btn = make_qta_btn(
            self,
            "new_inf_line",
            "Add new infinite line layer",
            func=partial(_add_new_inf_line, self.viewer),
        )
        self.new_region_btn.setParent(self)

        layout = hp.make_h_layout(parent=self, spacing=2, margin=0)
        layout.addWidget(self.new_shapes_btn)
        layout.addWidget(self.new_points_btn)
        layout.addWidget(self.new_region_btn)
        layout.addWidget(self.new_infline_btn)
        layout.addStretch(0)
        layout.addWidget(self.delete_btn)


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
            action="napari:reset_view",
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
