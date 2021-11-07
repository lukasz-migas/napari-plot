"""Layer buttons"""
from napari._qt.widgets.qt_viewer_buttons import QtDeleteButton
from qtpy.QtWidgets import QFrame, QHBoxLayout

from ..widgets.qt_image_button import QtViewerPushButton


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

        self.new_points_btn = QtViewerPushButton(
            self.viewer,
            "new_points",
            "Add new points layer",
            lambda: self.viewer.add_points(
                ndim=2,
                scale=self.viewer.layers.extent.step,
            ),
        )

        self.new_shapes_btn = QtViewerPushButton(
            self.viewer,
            "new_shapes",
            "Add new shapes layer",
            lambda: self.viewer.add_shapes(
                ndim=2,
                scale=self.viewer.layers.extent.step,
            ),
        )
        self.new_shapes_btn.setParent(self)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.new_shapes_btn)
        layout.addWidget(self.new_points_btn)
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

    def __init__(self, viewer, parent=None):
        super().__init__()

        self.viewer = viewer

        self.resetViewButton = QtViewerPushButton(
            self.viewer,
            "home",
            "Reset view (Ctrl-R)",
            lambda: self.viewer.reset_view(),
        )

        self.hidePanelButton = QtViewerPushButton(self.viewer, "minimise", "Hide control panel (Ctrl-H)")
        if parent is not None:
            self.hidePanelButton.clicked.connect(lambda: parent.on_toggle_controls_dialog())  # noqa

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.resetViewButton)
        layout.addStretch(0)
        layout.addWidget(self.hidePanelButton)
        self.setLayout(layout)
