"""QtImagePushButton"""

from napari._qt.widgets.qt_mode_buttons import QtModePushButton as _QtModePushButton
from napari._qt.widgets.qt_viewer_buttons import QtViewerPushButton as _QtViewerPushButton
from napari.settings import get_settings
from napari.utils.events.event_utils import connect_no_arg
from napari.utils.theme import _themes
from qtextra.widgets._qta_mixin import QtaMixin
from qtextra.widgets.qt_button_icon import QtImagePushButton


class QtViewerPushButton(QtaMixin, _QtViewerPushButton):
    """Overwritten class with added support for qtawesome icons."""

    def __init__(self, button_name, tooltip=None, slot=None):
        super().__init__(button_name="", tooltip=tooltip, slot=slot)
        connect_no_arg(get_settings().appearance.events.theme, self, "_update_qta")
        _themes.events.connect(self._update_from_event)
        self.set_qta(button_name)


class QtModePushButton(QtaMixin, _QtModePushButton):
    """Overwritten class with added support for qtawesome icons."""

    def __init__(self, layer, button_name, *, slot=None, tooltip=None):
        super().__init__(layer, "", tooltip=tooltip, slot=slot)
        self.set_qta(button_name)
        self.set_average()

        connect_no_arg(get_settings().appearance.events.theme, self, "_update_qta")
        _themes.events.connect(self._update_from_event)


class QtModeRadioButton(QtImagePushButton):
    """Overwritten class with added support for qtawesome icons."""

    def __init__(self, layer, button_name, mode, *, tooltip=None, checked=False):
        super().__init__()
        self.layer = layer
        self.setCheckable(True)
        self.setChecked(checked)
        self.set_qta(button_name)
        self.set_default_size(average=True)
        self.setToolTip(tooltip)
        self.mode = mode
        if mode is not None:
            self.toggled.connect(self._set_mode)

        connect_no_arg(get_settings().appearance.events.theme, self, "_update_qta")
        _themes.events.connect(self._update_from_event)

    def _set_mode(self, value: bool):
        """Toggle the mode associated with the layer."""
        with self.layer.events.mode.blocker(self._set_mode):
            if value:
                self.layer.mode = self.mode
