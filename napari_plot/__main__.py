"""napari-plot command line viewer."""

import argparse
import logging
import os
import sys
import typing as ty
import warnings
from ast import literal_eval
from pathlib import Path
from textwrap import wrap

from koyo.utilities import is_installed


class InfoAction(argparse.Action):
    """Print information."""

    def __call__(self, *args, **kwargs):
        # prevent unrelated INFO logs when doing "napari --info"

        logging.basicConfig(level=logging.WARNING)
        sys.exit()


def validate_unknown_args(unknown: ty.List[str]) -> ty.Dict[str, ty.Any]:
    """Convert a list of strings into a dict of valid kwargs for add_* methods.

    Will exit program if any of the arguments are unrecognized, or are
    malformed.  Converts string to python type using literal_eval.

    Parameters
    ----------
    unknown : List[str]
        a list of strings gathered as "unknown" arguments in argparse.

    Returns
    -------
    kwargs : Dict[str, Any]
        {key: val} dict suitable for the viewer.add_* methods where ``val``
        is a ``literal_eval`` result, or string.
    """

    from napari.components.viewer_model import valid_add_kwargs

    out: ty.Dict[str, ty.Any] = {}
    valid = set.union(*valid_add_kwargs().values())
    for i, arg in enumerate(unknown):
        if not arg.startswith("--"):
            continue

        if "=" in arg:
            key, value = arg.split("=", maxsplit=1)
        else:
            key = arg
        key = key.lstrip("-").replace("-", "_")

        if key not in valid:
            sys.exit(f"error: unrecognized arguments: {arg}")

        if "=" not in arg:
            try:
                value = unknown[i + 1]
                if value.startswith("--"):
                    raise IndexError
            except IndexError:
                sys.exit(f"error: argument {arg} expected one argument")
        try:
            value = literal_eval(value)
        except Exception:
            value = value

        out[key] = value
    return out


def parse_sys_argv():
    """Parse command line arguments."""

    from napari_plot import __version__
    from napari_plot.components.viewer_model import valid_add_kwargs

    kwarg_options = []
    for layer_type, keys in valid_add_kwargs().items():
        kwarg_options.append(f"  {layer_type.title()}:")
        keys = {k.replace("_", "-") for k in keys}
        lines = wrap(", ".join(sorted(keys)), break_on_hyphens=False)
        kwarg_options.extend([f"    {line}" for line in lines])

    parser = argparse.ArgumentParser(
        usage=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="optional layer-type-specific arguments (precede with '--'):\n" + "\n".join(kwarg_options),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="increase output verbosity",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"napari version {__version__}",
    )
    parser.add_argument(
        "--info",
        action=InfoAction,
        nargs=0,
        help="show system information and exit",
    )
    if is_installed("qtreload"):
        parser.add_argument(
            "--dev",
            action="store_true",
            help="show system information and exit",
        )
        parser.add_argument(
            "--dev_module",
            action="append",
            nargs="*",
            default=[],
            help="concatenate multiple modules that should be watched alongside `napari_plot` and `qtextra`.",
        )

    args, unknown = parser.parse_known_args()
    # this is a hack to allow using "=" as a key=value separator while also
    # allowing nargs='*' on the "paths" argument...
    # for idx, item in enumerate(reversed(args.paths)):
    #     if item.startswith("--"):
    #         unknown.append(args.paths.pop(len(args.paths) - idx - 1))
    kwargs = validate_unknown_args(unknown) if unknown else {}

    return args, kwargs


def _run():
    """Main program."""
    import logging

    from koyo.hooks import install_debugger_hook

    from napari_plot import Viewer, run

    args, kwargs = parse_sys_argv()

    # parse -v flags and set the appropriate logging level
    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(2, args.verbose)]  # prevent index error
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

    # check whether Dev mode was requested
    if args.dev:
        os.environ["NAPARI_PLOT_DEV"] = "1"
        install_debugger_hook()
        logging.info("Activated development mode.")
    # check if additional dev modules were requested
    if args.dev_module:
        dev_module = list(args.dev_module)
        os.environ["NAPARI_PLOT_DEV_MODULES"] = ",".join(dev_module)

    from napari_plot._qt.widgets.qt_splash_screen import QtSplashScreen

    splash = QtSplashScreen()
    splash.close()  # will close once event loop starts

    # viewer _must_  be kept around.
    # it will be referenced by the global window only
    # once napari has finished starting
    # but in the meantime if the garbage collector runs;
    # it will collect it and hang napari at start time.
    # in a way that is machine, os, time (and likely weather dependant).
    _viewer = Viewer()

    # viewer._window._qt_viewer._qt_open(
    #     args.paths,
    #     stack=args.stack,
    #     plugin=args.plugin,
    #     layer_type=args.layer_type,
    #     **kwargs,
    # )
    # if args.dev:
    #     import logging
    #
    #     from qtreload.qt_reload import QDevPopup
    #     from qtpy.QtWidgets import QPushButton
    #
    #     logging.getLogger("qtreload").setLevel(0)
    #
    #     window = viewer._window._qt_viewer
    #     dev_dlg = QDevPopup(
    #         window,
    #         modules=["koyo", "napari", "napari_plot"],
    #     )
    #     dev_dlg.qdev.evt_stylesheet.connect(lambda: window._update_theme())
    #     if hasattr(window, "statusbar"):
    #         window.dev_btn = QPushButton(window)
    #         window.dev_btn.setText("DevTools")
    #         window.dev_btn.setTooltip("Open developer tools.")
    #         window.dev_btn.clicked.connect(dev_dlg.show)
    #         window.statusbar.addPermanentWidget(window.dev_btn)  # type: ignore[attr-defined]

    run()


def _maybe_rerun_with_macos_fixes():
    """
    Apply some fixes needed in macOS, which might involve
    running this script again using a different sys.executable.

    1) Quick fix for Big Sur Python 3.9 and Qt 5.
       No relaunch needed.
    2) Using `pythonw` instead of `python`.
       This can be used to ensure we're using a framework
       build of Python on macOS, which fixes frozen menubar issues
       in some macOS versions.
    3) Make sure the menu bar uses 'napari' as the display name.
       This requires relaunching the app from a symlink to the
       desired python executable, conveniently named 'napari'.
    """
    from napari._qt import API_NAME

    # This import mus be here to raise exception about PySide6 problem

    if sys.platform != "darwin":
        return

    if "_NAPARI_PLOT_RERUN_WITH_FIXES" in os.environ:
        # This function already ran, do not recurse!
        # We also restore sys.executable to its initial value,
        # if we used a symlink
        if exe := os.environ.pop("_NAPARI_SYMLINKED_EXECUTABLE", ""):
            sys.executable = exe
        return

    import platform
    import subprocess
    from tempfile import mkdtemp

    # In principle, we will relaunch to the same python we were using
    executable = sys.executable
    cwd = Path.cwd()

    _MACOS_AT_LEAST_CATALINA = int(platform.release().split(".")[0]) >= 19
    _MACOS_AT_LEAST_BIG_SUR = int(platform.release().split(".")[0]) >= 20
    _RUNNING_CONDA = "CONDA_PREFIX" in os.environ
    _RUNNING_PYTHONW = "PYTHONEXECUTABLE" in os.environ

    # 1) quick fix for Big Sur py3.9 and qt 5
    # https://github.com/napari/napari/pull/1894
    if _MACOS_AT_LEAST_BIG_SUR and "6" not in API_NAME:
        os.environ["QT_MAC_WANTS_LAYER"] = "1"

    # Create the env copy now because the following changes
    # should not persist in the current process in case
    # we do not run the subprocess!
    env = os.environ.copy()

    # 2) Ensure we're always using a "framework build" on the latest
    # macOS to ensure menubar works without needing to refocus napari.
    # We try this for macOS later than the Catalina release
    # See https://github.com/napari/napari/pull/1554 and
    # https://github.com/napari/napari/issues/380#issuecomment-659656775
    # and https://github.com/ContinuumIO/anaconda-issues/issues/199
    if _MACOS_AT_LEAST_CATALINA and not _MACOS_AT_LEAST_BIG_SUR and _RUNNING_CONDA and not _RUNNING_PYTHONW:
        pythonw_path = Path(sys.exec_prefix) / "bin" / "pythonw"
        if pythonw_path.exists():
            # Use this one instead of sys.executable to relaunch
            # the subprocess
            executable = pythonw_path
        else:
            msg = (
                "pythonw executable not found.\n"
                "To unfreeze the menubar on macOS, "
                "click away from napari to another app, "
                "then reactivate napari. To avoid this problem, "
                "please install python.app in conda using:\n"
                "conda install -c conda-forge python.app"
            )
            warnings.warn(msg)

    # 3) Make sure the app name in the menu bar is 'napari', not 'python'
    tempdir = None
    _NEEDS_SYMLINK = (
        # When napari is launched from the conda bundle shortcut
        # it already has the right 'napari' name in the app title
        # and __CFBundleIdentifier is set to 'com.napari._(<version>)'
        "napari_plot" not in os.environ.get("__CFBundleIdentifier", "")
        # with a sys.executable named napari,
        # macOS should have picked the right name already
        or os.path.basename(executable) != "napari_plot"
    )
    if _NEEDS_SYMLINK:
        tempdir = mkdtemp(prefix="symlink-to-fix-macos-menu-name-")
        # By using a symlink with basename napari
        # we make macOS take 'napari' as the program name
        napari_link = os.path.join(tempdir, "napari_plot")
        os.symlink(executable, napari_link)
        # Pass original executable to the subprocess so it can restore it later
        env["_NAPARI_PLOT_SYMLINKED_EXECUTABLE"] = executable
        executable = napari_link

    # if at this point 'executable' is different from 'sys.executable', we
    # need to launch the subprocess to apply the fixes
    if sys.executable != executable:
        env["_NAPARI_PLOT_RERUN_WITH_FIXES"] = "1"
        if Path(sys.argv[0]).name == "napari_plot":
            # launched through entry point, we do that again to avoid
            # issues with working directory getting into sys.path (#5007)
            cmd = [executable, sys.argv[0]]
        else:  # we assume it must have been launched via '-m' syntax
            cmd = [executable, "-m", "napari_plot"]

        # this fixes issues running from a venv/virtualenv based virtual
        # environment with certain python distributions (e.g. pyenv, asdf)
        env["PYTHONEXECUTABLE"] = sys.executable

        # Append original command line arguments.
        if len(sys.argv) > 1:
            cmd.extend(sys.argv[1:])
        try:
            result = subprocess.run(cmd, env=env, cwd=cwd)
            sys.exit(result.returncode)
        finally:
            if tempdir is not None:
                import shutil

                shutil.rmtree(tempdir)


def main():
    # There a number of macOS issues we can fix with env vars
    # and/or relaunching a subprocess
    _maybe_rerun_with_macos_fixes()

    # Prevent https://github.com/napari/napari/issues/3415
    # This one fix is needed _after_ a potential relaunch,
    # that's why it's here and not in _maybe_rerun_with_macos_fixes()
    if sys.platform == "darwin":
        import multiprocessing

        multiprocessing.set_start_method("fork")

    _run()


if __name__ == "__main__":
    sys.exit(main())
