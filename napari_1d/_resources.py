"""Resources."""
from napari_plugin_engine import napari_hook_implementation
from pathlib import Path

HERE = Path(__file__).parent


@napari_hook_implementation
def napari_experimental_provide_icons():
    """Provide icons to """
    return list((HERE / "resources" / "icons").glob("*.svg"))


@napari_hook_implementation
def napari_experimental_provide_qss():
    """A basic implementation of the napari_get_reader hook specification."""
    return list((HERE / "_qt" / "styles").glob("*.qss"))
