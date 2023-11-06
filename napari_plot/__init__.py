"""Init"""
try:
    from napari_plot._version import version as __version__
except ImportError:
    __version__ = "unknown"

# Need to import to ensure that `napari_plot` is included in the auto-class generator
from napari_plot.utils import _register  # isort:skip noqa

from napari_plot._contribution import napari_experimental_provide_dock_widget  # noqa: F401
from napari_plot._qt.qt_event_loop import run  # noqa: F401
from napari_plot.components.viewer_model import ViewerModel as ViewerModel1D  # noqa: F401

# Need to import to ensure that stylesheets are included in the `STYLES` dictionary
from napari_plot.resources import STYLES, ICONS  # noqa: F401
from napari_plot.viewer import Viewer  # noqa: F401

del _register
