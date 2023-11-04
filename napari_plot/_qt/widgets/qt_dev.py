"""Development widgets."""
import typing as ty
import logging

logger = logging.getLogger()

if ty.TYPE_CHECKING:
    from qtreload.qt_reload import QtReloadWidget


def qdev(parent=None, modules: ty.Iterable[str] = ("napari", "napari_plot")) -> "QtReloadWidget":
    """Create reload widget."""
    from qtreload.qt_reload import QtReloadWidget

    logger.debug(f"Creating reload widget for modules: {modules}.")
    return QtReloadWidget(modules, parent=parent)
