import pytest

from napari_plot._qt.widgets.qt_dev import QtReload


@pytest.fixture
def setup_widget(qtbot):
    """Setup panel"""

    def _widget() -> QtReload:
        widget = QtReload()
        qtbot.addWidget(widget)
        return widget

    return _widget


class TestQtReload:
    def test_init(self, qtbot, setup_widget, monkeypatch):
        monkeypatch.setattr(QtReload, "show", lambda *a: None)
        widget = setup_widget()
        assert widget
        assert widget._path is not None
        paths = widget._get_paths(widget._path)
        assert len(paths) > 0
