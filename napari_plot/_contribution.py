"""Napari contributions in old npe1 style."""
from napari_plugin_engine import napari_hook_implementation

from napari_plot._plot_widget import NapariPlotWidget
from napari_plot._scatter_widget import ScatterPlotWidget


@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    """Return dock widget."""
    return [
        (NapariPlotWidget, {"area": "bottom", "name": "Napari-Plot"}),
        (ScatterPlotWidget, {"area": "right", "name": "Napari-Plot (Scatter)"}),
    ]
