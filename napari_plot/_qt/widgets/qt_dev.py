"""Development widgets."""
import typing as ty

if ty.TYPE_CHECKING:
    from qtreload.qt_reload import QtReloadWidget


def qdev(parent=None, modules: ty.Iterable[str] = ("napari", "napari-plot")) -> "QtReloadWidget":
    """Create reload widget."""
    from qtreload.qt_reload import QtReloadWidget

    return QtReloadWidget(modules, parent=parent)
