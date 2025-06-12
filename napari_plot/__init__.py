"""Init"""

try:
    from napari_plot._version import version as __version__
except ImportError:
    __version__ = "unknown"

# Need to import to ensure that `napari_plot` is included in the auto-class generator
from napari_plot.utils import _register  # isort:skip noqa

from napari_plot._contribution import napari_experimental_provide_dock_widget
from napari_plot._plot_widget import NapariPlotWidget
from napari_plot._qt.qt_event_loop import run
from napari_plot._scatter_widget import ScatterPlotWidget
from napari_plot.components.viewer_model import ViewerModel as ViewerModel1D
from napari_plot.resources import load_assets
from napari_plot.viewer import Viewer

del _register

load_assets()

__all__ = (
    "NapariPlotWidget",
    "ScatterPlotWidget",
    "Viewer",
    "ViewerModel1D",
    "__version__",
    "load_assets",
    "napari_experimental_provide_dock_widget",
    "run",
)
