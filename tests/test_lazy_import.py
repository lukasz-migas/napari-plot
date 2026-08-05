"""Test lazy imports."""

from npe2 import PluginManifest
from npe2.manifest.utils import import_python_name

import napari_plot


def test_lazy_imports():
    """Test that lazy imports work."""
    # Accessing the attributes should trigger the lazy import
    assert "NapariPlotWidget" in dir(napari_plot)
    assert "ScatterPlotWidget" in dir(napari_plot)
    assert "Viewer" in dir(napari_plot)
    assert "ViewerModel" in dir(napari_plot)
    assert "run" in dir(napari_plot)
    assert "load_assets" in dir(napari_plot)

    from napari_plot import NapariPlotWidget, ScatterPlotWidget, Viewer, ViewerModel, load_assets, run

    assert NapariPlotWidget is not None, "NapariPlotWidget should be imported"
    assert ScatterPlotWidget is not None, "ScatterPlotWidget should be imported"
    assert Viewer is not None, "Viewer should be imported"
    assert ViewerModel is not None, "ViewerModel should be imported"
    assert run is not None, "run should be imported"
    assert load_assets is not None, "load_assets should be imported"


def test_all_public_exports_are_importable():
    """Every advertised package export should resolve at runtime."""
    for name in napari_plot.__all__:
        assert getattr(napari_plot, name) is not None


def test_manifest_commands_are_importable():
    """The widget command targets in the packaged npe2 manifest should import."""
    manifest = PluginManifest.from_file(napari_plot.__path__[0] + "/napari.yaml")

    for command in manifest.contributions.commands:
        assert import_python_name(command.python_name) is not None
