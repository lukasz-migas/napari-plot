"""Init"""
try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"

# Need to import to ensure that `napari_1d` is included in the auto-class generator
from .utils import _register  # isort:skip noqa
from ._dock_widget import napari_experimental_provide_dock_widget  # noqa: F401
from ._qt.qt_event_loop import run  # noqa: F401
from .components.viewer_model import ViewerModel as ViewerModel1D  # noqa: F401
from .viewer import Viewer  # noqa: F401

del _register
