"""Init"""

try:
    from napari_plot._version import version as __version__
except ImportError:
    __version__ = "unknown"

# Need to import to ensure that `napari_plot` is included in the auto-class generator
from napari_plot.utils import _register  # isort:skip noqa

from napari_plot._contribution import napari_experimental_provide_dock_widget
from napari_plot._qt.qt_event_loop import run
from napari_plot.components.viewer_model import ViewerModel as ViewerModel1D

# Need to import to ensure that stylesheets are included in the `STYLES` dictionary
from napari_plot.resources import ICONS, STYLES
from napari_plot.viewer import Viewer

del _register
