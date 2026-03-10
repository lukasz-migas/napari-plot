"""Test lazy imports."""

import napari_plot


def test_lazy_imports():
    """Test that lazy imports work."""
    # Accessing the attributes should trigger the lazy import
    assert "NapariPlotWidget" in dir(napari_plot)
    assert "ScatterPlotWidget" in dir(napari_plot)
    assert "Viewer" in dir(napari_plot)
    assert "ViewerModel" in dir(napari_plot)
    assert "run" in dir(napari_plot)

    from napari_plot import NapariPlotWidget, ScatterPlotWidget, Viewer, ViewerModel, run

    assert NapariPlotWidget is not None, "NapariPlotWidget should be imported"
    assert ScatterPlotWidget is not None, "ScatterPlotWidget should be imported"
    assert Viewer is not None, "Viewer should be imported"
    assert ViewerModel is not None, "ViewerModel should be imported"
    assert run is not None, "run should be imported"
