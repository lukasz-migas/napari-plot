"""Init"""
# Need to import to ensure that `napari_1d` is included in the auto-class generator
from ._dock_widget import napari_experimental_provide_dock_widget  # noqa: F401
from .components.viewer_model import ViewerModel as ViewerModel1D  # noqa: F401
from .utils import _register  # noqa

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"

del _register
