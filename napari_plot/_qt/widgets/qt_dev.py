"""Development widgets."""
import importlib
import pkgutil
from pathlib import Path

from qtpy.QtCore import QFileSystemWatcher
from qtpy.QtWidgets import QHBoxLayout, QLabel, QWidget
from superqt.utils import qthrottled

from napari_plot.utils.vendored.pydevd_reload import xreload


def get_import_path(module: str) -> Path:
    """Get module path."""
    module = pkgutil.get_loader(module)
    if module is None:
        return None
    path = Path(module.get_filename())
    return path.parent


def path_to_module(path: str) -> str:
    """Turn path into module name."""
    module = path.split("napari_plot\\")[1]
    return "napari_plot." + module.replace("\\", ".").replace(".py", "")


def get_parent_module(module: str):
    """Get parent module."""
    return ".".join(module.split(".")[:-1])


class QtReload(QWidget):
    """Reload Widget"""

    def __init__(self, parent=None, module: str = "napari_plot", auto_connect: bool = True):
        super().__init__(parent=parent)
        self._watcher = QFileSystemWatcher()

        self._info = QLabel()

        layout = QHBoxLayout()
        layout.addWidget(self._info, stretch=True)
        self.setLayout(layout)

        self._path = get_import_path(module)
        if self._path and auto_connect:
            self.setup_paths()

    def setup_paths(self):
        """Setup paths.""" ""
        self._add_filenames()
        self._watcher.fileChanged.connect(self.on_reload_file)
        # self._add_directories()
        # self._watcher.directoryChanged.connect(self.on_reload_directory)

    @staticmethod
    def _get_paths(path: Path):
        paths = []
        for path in path.glob("**/*.py"):
            if path.name == "__init__.py":
                continue
            paths.append(str(path))
        paths = list(set(paths))
        return paths

    def _add_filenames(self):
        """Set paths."""
        paths = self._get_paths(self._path)
        self._info.setText(f"Added {len(paths)} paths to watcher")
        self._watcher.addPaths(paths)

    @staticmethod
    def _get_directories(path):
        paths = []
        for path in path.glob("**/*.py"):
            if path.name == "__init__.py":
                continue
            paths.append(str(path.parent))
        paths = list(set(paths))
        return paths

    def _add_directories(self):
        paths = self._get_directories(self._path)
        self._info.setText(f"Added {len(paths)} paths to watcher")
        self._watcher.addPaths(paths)

    @qthrottled(timeout=500, leading=False)
    def on_reload_file(self, path: str):
        """Reload all modules."""
        self._reload(path)

    def _reload(self, path: str):
        module = path_to_module(path)
        try:
            res = xreload(importlib.import_module(module))
            self._info.setText(f"'{module}' (changed={res})")
            print(f"'{module}' (changed={res})")
        except Exception as e:
            print(f"Failed to reload '{path}' {module}' Error={e}...")

    def on_reload_directory(self, path: str):
        """Reload all modules in directory."""
        paths = self._get_paths(Path(path))
        for path in paths:
            self._reload(path)
