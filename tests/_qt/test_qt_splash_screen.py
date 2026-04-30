import pytest

from napari_plot._qt.widgets.qt_splash_screen import QtSplashScreen


@pytest.fixture
def setup_widget(qtbot):
    """Setup panel"""

    def _widget() -> QtSplashScreen:
        widget = QtSplashScreen()
        qtbot.addWidget(widget)
        return widget

    return _widget


class TestQtSplashScreen:
    def test_init(self, qtbot, setup_widget, monkeypatch):
        monkeypatch.setattr(QtSplashScreen, "show", lambda *a: None)
        widget = setup_widget()
        assert widget
