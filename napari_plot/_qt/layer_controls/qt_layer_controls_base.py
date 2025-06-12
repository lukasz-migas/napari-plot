"""Base layer controls"""

import typing as ty

import qtextra.helpers as hp
from napari.layers.base._base_constants import BLENDING_TRANSLATIONS, Blending, Mode
from napari.utils.action_manager import action_manager
from napari.utils.events import disconnect_events
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QButtonGroup, QFormLayout, QFrame, QGridLayout

from napari_plot._qt.widgets.qt_icon_button import QtModePushButton, QtModeRadioButton

# opaque and minimum blending do not support changing alpha (opacity)
NO_OPACITY_BLENDING_MODES = {str(Blending.MINIMUM), str(Blending.OPAQUE)}


class QtLayerControls(QFrame):
    """Superclass for all the other LayerControl classes.

    This class is never directly instantiated anywhere.

    Parameters
    ----------
    layer : napari_plot.layers.Layer
        An instance of a layer.

    Attributes
    ----------
    layer : napari_plot.layers.Layer
        An instance of a layer.
    layout : qtpy.QtWidgets.QGridLayout
        Layout of Qt widget controls for the layer.
    blending_combobox : qtpy.QtWidgets.QComboBox
        Dropdown widget to select blending mode of layer.
    opacity_slider : qtpy.QtWidgets.QSlider
        Slider controlling opacity of the layer.
    """

    MODE = Mode
    PAN_ZOOM_ACTION_NAME = ""
    TRANSFORM_ACTION_NAME = ""

    def __init__(self, layer):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setObjectName("layer")
        self.setMouseTracking(True)

        self._ndisplay: int = 2
        self._EDIT_BUTTONS: tuple = ()
        self._MODE_BUTTONS: dict = {}

        self.layer = layer
        self.layer.events.blending.connect(self._on_blending_change)
        self.layer.events.opacity.connect(self._on_opacity_change)

        # layout where all widgets will go
        self.setLayout(QFormLayout(self))
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(4)
        self.layout().setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        # Buttons
        self.button_group = QButtonGroup(self)
        self.panzoom_button = self._radio_button(
            layer,
            "pan_zoom",
            self.MODE.PAN_ZOOM,
            False,
            self.PAN_ZOOM_ACTION_NAME,
            extra_tooltip_text="(or hold Space)",
            checked=True,
        )
        self.transform_button = self._radio_button(
            layer,
            "transform",
            self.MODE.TRANSFORM,
            True,
            self.TRANSFORM_ACTION_NAME,
            extra_tooltip_text="\nAlt + Left mouse click over this button to reset",
        )
        self.transform_button.installEventFilter(self)

        self.button_grid = QGridLayout()
        self.button_grid.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.button_grid.addWidget(self.panzoom_button, 0, 6)
        self.button_grid.addWidget(self.transform_button, 0, 7)
        self.button_grid.setContentsMargins(5, 0, 0, 5)
        self.button_grid.setColumnStretch(0, 1)
        self.button_grid.setSpacing(4)

        # Control widgets
        self.opacity_label = hp.make_label(self, "Opacity:")
        self.opacity_slider = hp.make_slider_with_text(self, tooltip="Opacity", focus_policy=Qt.FocusPolicy.NoFocus)
        self.opacity_slider.valueChanged.connect(self.on_change_opacity)
        self._on_opacity_change()

        # Blending
        self.blending_combobox = hp.make_combobox(self)
        hp.set_combobox_data(self.blending_combobox, BLENDING_TRANSLATIONS, self.layer.blending)
        self.blending_combobox.currentTextChanged.connect(self.on_change_blending)

        # opaque and minimum blending do not support changing alpha
        self.opacity_slider.setEnabled(self.layer.blending not in NO_OPACITY_BLENDING_MODES)
        self.opacity_label.setEnabled(self.layer.blending not in NO_OPACITY_BLENDING_MODES)

        if self.__class__ == QtLayerControls:
            # This base class is only instantiated in tests. When it's not a
            # concrete subclass, we need to parent the button_grid to the
            # layout so that qtbot will correctly clean up all instantiated
            # widgets.
            self.layout().addRow(self.button_grid)

    def on_change_opacity(self, value):
        """Change opacity value on the layer model.

        Parameters
        ----------
        value : float
            Opacity value for shapes.
            Input range 0 - 100 (transparent to fully opaque).
        """
        with self.layer.events.blocker(self._on_opacity_change):
            self.layer.opacity = value / 100

    def _on_opacity_change(self, _event=None):
        """Receive layer model opacity change event and update opacity slider.

        Parameters
        ----------
        _event : napari.utils.event.Event, optional
            The napari event that triggered this method, by default None.
        """
        with self.layer.events.opacity.blocker():
            self.opacity_slider.setValue(int(self.layer.opacity * 100))

    def on_change_blending(self, _text):
        """Change blending mode on the layer model.

        Parameters
        ----------
        _text : str
            Name of blending mode, eg: 'translucent', 'additive', 'opaque'.
        """
        self.layer.blending = self.blending_combobox.currentData()
        # opaque and minimum blending do not support changing alpha
        self.opacity_slider.setEnabled(self.layer.blending not in NO_OPACITY_BLENDING_MODES)
        self.opacity_label.setEnabled(self.layer.blending not in NO_OPACITY_BLENDING_MODES)

        blending_tooltip = ""
        if self.layer.blending == str(Blending.MINIMUM):
            blending_tooltip = ("`minimum` blending mode works best with inverted colormaps with a white background.",)
        self.blending_combobox.setToolTip(blending_tooltip)
        self.layer.help = blending_tooltip

    def _on_blending_change(self, _event=None):
        """Receive layer model blending mode change event and update slider.

        Parameters
        ----------
        _event : napari.utils.event.Event, optional
            The napari event that triggered this method, by default None.
        """
        with self.layer.events.blending.blocker():
            hp.set_combobox_current_index(self.blending_combobox, self.layer.blending)

    def _radio_button(
        self,
        layer,
        btn_name,
        mode,
        edit_button,
        action_name,
        extra_tooltip_text="",
        **kwargs,
    ):
        """
        Convenience local function to create a RadioButton and bind it to
        an action at the same time.

        Parameters
        ----------
        layer : napari.layers.Layer
            The layer instance that this button controls.n
        btn_name : str
            name fo the button
        mode : Enum
            Value Associated to current button
        edit_button: bool
            True if the button corresponds to edition operations. False otherwise.
        action_name : str
            Action triggered when button pressed
        extra_tooltip_text : str
            Text you want added after the automatic tooltip set by the
            action manager
        **kwargs:
            Passed to napari._qt.widgets.qt_mode_button.QtModeRadioButton

        Returns
        -------
        button: napari._qt.widgets.qt_mode_button.QtModeRadioButton
            button bound (or that will be bound to) to action `action_name`

        Notes
        -----
        When shortcuts are modifed/added/removed via the action manager, the
        tooltip will be updated to reflect the new shortcut.
        """
        action_name = f"napari:{action_name}"
        btn = QtModeRadioButton(layer, btn_name, mode, **kwargs)
        action_manager.bind_button(action_name, btn, extra_tooltip_text=extra_tooltip_text)
        self._MODE_BUTTONS[mode] = btn
        self.button_group.addButton(btn)
        if edit_button:
            self._EDIT_BUTTONS += (btn,)
        return btn

    def _action_button(
        self,
        layer,
        btn_name: str,
        slot: ty.Callable,
        tooltip: str,
        edit_button: bool = False,
    ):
        btn = QtModePushButton(layer, btn_name, slot=slot, tooltip=tooltip)
        if edit_button:
            self._EDIT_BUTTONS += (btn,)
        return btn

    def _on_mode_change(self, event):
        """
        Update ticks in checkbox widgets when image based layer mode changed.

        Available modes for base layer are:
        * PAN_ZOOM
        * TRANSFORM

        Parameters
        ----------
        event : napari.utils.event.Event
            The napari event that triggered this method.

        Raises
        ------
        ValueError
            Raise error if event.mode is not PAN_ZOOM or TRANSFORM.
        """
        if event.mode in self._MODE_BUTTONS:
            self._MODE_BUTTONS[event.mode].setChecked(True)
        else:
            raise ValueError(f"Mode '{event.mode}' not recognized")

    def close(self):
        """Disconnect events when widget is closing."""
        disconnect_events(self.layer.events, self)
        for child in self.children():
            close_method = getattr(child, "close", None)
            if close_method is not None:
                close_method()
        super().close()
