import collections
import gc
import os
import sys
import typing as ty
import warnings
from weakref import WeakSet

import pytest

if ty.TYPE_CHECKING:
    from pytest import FixtureRequest

COUNTER = 0
_SAVE_GRAPH_OPNAME = "--save-leaked-object-graph-np"
_SHOW_VIEWER = "--show-napari-plot-viewer"


def pytest_addoption(parser):
    parser.addoption(
        _SHOW_VIEWER,
        action="store_true",
        default=False,
        help="don't show viewer during tests",
    )

    parser.addoption(
        _SAVE_GRAPH_OPNAME,
        action="store_true",
        default=False,
        help="Try to save a graph of leaked object's reference (need objgraph" "and graphviz installed",
    )


def fail_obj_graph(Klass):
    """
    Fail is a given class _instances weakset is non empty and print the object graph.
    """

    try:
        import objgraph
    except ImportError:
        return

    if not len(Klass._instances) == 0:
        global COUNTER
        COUNTER += 1
        import gc

        gc.collect()

        filename = f"{Klass.__name__}-leak-backref-graph-{COUNTER}.pdf"
        objgraph.show_backrefs(
            list(Klass._instances),
            max_depth=20,
            filename=filename,
        )

        # DO not remove len, this can break as C++ obj are gone, but python objects
        # still hang around and _repr_ would crash.
        assert False, len(Klass._instances)


@pytest.fixture
def make_napari_plot_viewer(qtbot, request: "FixtureRequest"):
    """A fixture function that creates a napari viewer for use in testing.

    Use this fixture as a function in your tests:

        viewer = make_napari_viewer()

    It accepts all the same arguments as napari.Viewer, plus the following
    test-related paramaters:

    ViewerClass : Type[napari.Viewer], optional
        Override the viewer class being used.  By default, will
        use napari.viewer.Viewer
    strict_qt : bool or str, optional
        If True, a check will be performed after test cleanup to make sure that
        no top level widgets were created and *not* cleaned up during the
        test.  If the string "raise" is provided, an AssertionError will be
        raised.  Otherwise a warning is emitted.
        By default, this is False unless the test is being performed within
        the napari package.
        This can be made globally true by setting the 'NAPARI_STRICT_QT'
        environment variable.

    Examples
    --------
    >>> def test_adding_shapes(make_napari_plot_viewer):
    ...     viewer = make_napari_plot_viewer()
    ...     viewer.add_shapes()
    ...     assert len(viewer.layers) == 1

    >>> def test_something_with_strict_qt_tests(make_napari_plot_viewer):
    ...     viewer = make_napari_plot_viewer(strict_qt=True)
    """
    from qtpy.QtWidgets import QApplication

    from napari_plot import Viewer
    from napari_plot._qt.qt_viewer import QtViewer

    # from napari.settings import get_settings
    #
    # settings = get_settings()
    # settings.reset()

    viewers: WeakSet[Viewer] = WeakSet()

    # may be overridden by using `make_napari_plot_viewer(strict=True)`
    _strict = False

    initial = QApplication.topLevelWidgets()
    prior_exception = getattr(sys, "last_value", None)
    is_internal_test = request.module.__name__.startswith("napari.")  # this should use `napari_plot.`

    def actual_factory(
        *model_args,
        ViewerClass=Viewer,
        strict_qt=is_internal_test or os.getenv("NAPARI_STRICT_QT"),
        **model_kwargs,
    ):
        nonlocal _strict
        _strict = strict_qt

        should_show = request.config.getoption(_SHOW_VIEWER)
        model_kwargs["show"] = model_kwargs.pop("show", should_show)
        viewer = ViewerClass(*model_args, **model_kwargs)
        viewers.add(viewer)

        return viewer

    yield actual_factory

    # # Some tests might have the viewer closed, so this call will not be able
    # # to access the window.
    # with suppress(AttributeError):
    #     get_settings().reset()

    # close viewers, but don't saving window settings while closing
    for viewer in viewers:
        # if hasattr(viewer.window, "_qt_window"):
        #     with patch.object(viewer.window._qt_window, "_save_current_window_settings"):
        #         viewer.close()
        # else:
        viewer.close()

    gc.collect()

    if request.config.getoption(_SAVE_GRAPH_OPNAME):
        fail_obj_graph(QtViewer)

    # _do_not_inline_below = len(QtViewer._instances)
    # # do not inline to avoid pytest trying to compute repr of expression.
    # # it fails if C++ object gone but not Python object.
    # assert _do_not_inline_below == 0

    # only check for leaked widgets if an exception was raised during the test,
    # or "strict" mode was used.
    if _strict and getattr(sys, "last_value", None) is prior_exception:
        QApplication.processEvents()
        leak = set(QApplication.topLevelWidgets()).difference(initial)
        # still not sure how to clean up some of the remaining vispy
        # vispy.app.backends._qt.CanvasBackendDesktop widgets...
        if any([n.__class__.__name__ != "CanvasBackendDesktop" for n in leak]):
            # just a warning... but this can be converted to test errors
            # in pytest with `-W error`
            msg = f"""The following Widgets leaked!: {leak}.

            Note: If other tests are failing it is likely that widgets will leak
            as they will be (indirectly) attached to the tracebacks of previous failures.
            Please only consider this an error if all other tests are passing.\n\n
            """
            # Explanation notes on the above: While we are indeed looking at the
            # difference in sets of widgets between before and after, new object can
            # still not be garbage collected because of it.
            # in particular with VisPyCanvas, it looks like if a traceback keeps
            # contains the type, then instances are still attached to the type.
            # I'm not too sure why this is the case though.
            if _strict == "raise":
                raise AssertionError(msg)
            else:
                warnings.warn(msg)


@pytest.fixture
def MouseEvent():
    """Create a subclass for simulating vispy mouse events.

    Returns
    -------
    Event : Type
        A new tuple subclass named Event that can be used to create a
        NamedTuple object with fields "type" and "is_dragging".
    """
    return collections.namedtuple(
        "Event",
        field_names=[
            "type",
            "is_dragging",
            "position",
            "view_direction",
            "dims_displayed",
            "dims_point",
        ],
    )
