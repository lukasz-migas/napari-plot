import os
import runpy
from pathlib import Path

import napari
import pytest
from napari._qt.qt_main_window import Window as NapariWindow
from qtpy import API_NAME

import napari_plot
from napari_plot._qt.qt_main_window import Window

# not testing these examples
skip = [
    "live_update_multiple_lines.py",  # has very long-running thread which would take a lifetime
    "live_update_lines.py",  # has very long-running thread which would take a lifetime
    "live_update_scatter.py",  # has very long-running thread which would take a lifetime
]


EXAMPLE_DIR = Path(napari_plot.__file__).parent.parent / "examples"
# using f.name here and re-joining at `run_path()` for test key presentation
# (works even if the examples list is empty, as opposed to using an ids lambda)
examples = []
for f in EXAMPLE_DIR.glob("*.py"):
    if f.name in skip:
        continue
    examples.append(f.name)

EXAMPLE_WITH_NAPARI_DIR = Path(napari_plot.__file__).parent.parent / "examples_with_napari"
# using f.name here and re-joining at `run_path()` for test key presentation
# (works even if the examples list is empty, as opposed to using an ids lambda)
examples_with_napari = []
for f in EXAMPLE_WITH_NAPARI_DIR.glob("*.py"):
    if f.name in skip:
        continue
    examples_with_napari.append(f.name)


# still some CI segfaults, but only on windows with pyqt5
if os.getenv("CI") and os.name == "nt" and API_NAME == "PyQt5":
    examples, examples_with_napari = [], []


@pytest.mark.filterwarnings("ignore")
@pytest.mark.skipif(not examples, reason="No examples were found.")
@pytest.mark.parametrize("filename", examples)
def test_examples(filename, monkeypatch):
    """Test that all of our examples are still working without warnings."""

    # hide viewer window
    monkeypatch.setattr(Window, "show", lambda *a: None)
    # prevent running the event loop
    monkeypatch.setattr(napari_plot, "run", lambda *a, **k: None)

    # make sure our sys.excepthook override doesn't hide errors
    def raise_errors(etype, value, tb):
        raise value

    # run the example!
    try:
        runpy.run_path(str(EXAMPLE_DIR / filename))
    except SystemExit as e:
        # we use sys.exit(0) to gracefully exit from examples
        if e.code != 0:
            raise
    finally:
        napari_plot.Viewer.close_all()


@pytest.mark.filterwarnings("ignore")
@pytest.mark.skipif(not examples_with_napari, reason="No examples were found.")
@pytest.mark.parametrize("filename", examples_with_napari)
def test_examples_with_napari(filename, monkeypatch):
    """Test that all of our examples are still working without warnings."""

    # hide viewer window
    monkeypatch.setattr(NapariWindow, "show", lambda *a: None)
    # prevent running the event loop
    monkeypatch.setattr(napari, "run", lambda *a, **k: None)

    # make sure our sys.excepthook override doesn't hide errors
    def raise_errors(etype, value, tb):
        raise value

    # run the example!
    try:
        runpy.run_path(str(EXAMPLE_WITH_NAPARI_DIR / filename))
    except SystemExit as e:
        # we use sys.exit(0) to gracefully exit from examples
        if e.code != 0:
            raise
    finally:
        napari.Viewer.close_all()  # TODO: change to `close_all`
