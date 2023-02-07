"""Layer buttons"""
from napari._qt.widgets.qt_viewer_buttons import QtDeleteButton
from qtpy.QtWidgets import QFrame, QHBoxLayout

from napari_plot._qt.widgets.qt_icon_button import QtViewerPushButton as QtQtaViewerPushButton


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
        self.delete_btn = QtDeleteButton(self.viewer)
        self.delete_btn.setParent(self)

        self.new_points_btn = QtQtaViewerPushButton(
            "new_points",
            "Add new points layer",
            slot=lambda: self.viewer.add_points(
                ndim=2,
                scale=self.viewer.layers.extent.step,
            ),
        )

        self.new_shapes_btn = QtQtaViewerPushButton(
            "new_shapes",
            "Add new shapes layer",
            slot=lambda: self.viewer.add_shapes(
                ndim=2,
                scale=self.viewer.layers.extent.step,
            ),
        )
        self.new_shapes_btn.setParent(self)

        self.new_region_btn = QtQtaViewerPushButton(
            "new_region",
            "Add new region layer",
            slot=lambda: self.viewer.add_region(
                scale=self.viewer.layers.extent.step,
                opacity=0.75,
            ),
        )
        self.new_region_btn.setParent(self)

        self.new_infline_btn = QtQtaViewerPushButton(
            "new_inf_line",
            "Add new region layer",
            slot=lambda: self.viewer.add_inf_line(
                scale=self.viewer.layers.extent.step,
            ),
        )
        self.new_region_btn.setParent(self)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.new_shapes_btn)
        layout.addWidget(self.new_points_btn)
        layout.addWidget(self.new_region_btn)
        layout.addWidget(self.new_infline_btn)
        layout.addStretch(0)
        layout.addWidget(self.delete_btn)
        self.setLayout(layout)


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

        self.resetViewButton = QtQtaViewerPushButton(
            "home",
            "Reset view (Ctrl-R)",
            lambda: self.viewer.reset_view(),
        )
        # only add console if its QtViewer
        self.consoleButton = None
        if kwargs.get("dock_console", False):
            self.consoleButton = QtQtaViewerPushButton("ipython", "Show/hide console panel")
            self.consoleButton.clicked.connect(lambda: parent.on_toggle_console_visibility())

        self.hidePanelButton = QtQtaViewerPushButton("minimise", "Hide control panel (Ctrl-H)")
        if parent is not None:
            self.hidePanelButton.clicked.connect(lambda: parent.on_toggle_controls_dialog())  # noqa
        if kwargs.get("dock_controls", False):
            self.hidePanelButton.setVisible(False)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.resetViewButton)
        if self.consoleButton is not None:
            layout.addWidget(self.consoleButton)
        layout.addStretch(0)
        layout.addWidget(self.hidePanelButton)
        self.setLayout(layout)
