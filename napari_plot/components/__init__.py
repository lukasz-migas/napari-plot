# Note that importing _viewer_key_bindings is needed as the Viewer gets
# decorated with keybindings during that process, but it is not directly needed
# by our users and so is deleted below
from . import _viewer_key_bindings
from .viewer_model import ViewerModel  # noqa: F401

del _viewer_key_bindings
