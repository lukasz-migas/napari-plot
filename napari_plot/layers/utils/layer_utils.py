from __future__ import annotations

import functools
import inspect
import typing as ty

# from napari.utils.action_manager import action_manager as n_action_manager
from napari_plot.utils.action_manager import action_manager


def register_layer_action(
    keymapprovider,
    description: str,
    repeatable: bool = False,
    shortcuts: ty.Optional[ty.Union[str, list[str]]] = None,
) -> ty.Callable[[ty.Callable], ty.Callable]:
    """
    Convenient decorator to register an action with the current Layers

    It will use the function name as the action name. We force the description
    to be given instead of function docstring for translation purpose.


    Parameters
    ----------
    keymapprovider : KeymapProvider
        class on which to register the keybindings - this will typically be
        the instance in focus that will handle the keyboard shortcut.
    description : str
        The description of the action, this will typically be translated and
        will be what will be used in tooltips.
    repeatable : bool
        A flag indicating whether the action autorepeats when key is held
    shortcuts : str | List[str]
        Shortcut to bind by default to the action we are registering.

    Returns
    -------
    function:
        Actual decorator to apply to a function. Given decorator returns the
        function unmodified to allow decorator stacking.

    """

    def _inner(func: ty.Callable) -> ty.Callable:
        nonlocal shortcuts
        name = "napari_plot:" + func.__name__

        # n_action_manager.register_action(
        #     name=name,
        #     command=func,
        #     description=description,
        #     keymapprovider=keymapprovider,
        #     repeatable=repeatable,
        # )
        action_manager.register_action(
            name=name,
            command=func,
            description=description,
            keymapprovider=keymapprovider,
            repeatable=repeatable,
        )
        if shortcuts:
            if isinstance(shortcuts, str):
                shortcuts = [shortcuts]

            for shortcut in shortcuts:
                # n_action_manager.bind_shortcut(name, shortcut)
                action_manager.bind_shortcut(name, shortcut)
        return func

    return _inner


def register_layer_attr_action(
    keymapprovider,
    description: str,
    attribute_name: str,
    shortcuts=None,
) -> ty.Callable[[ty.Callable], ty.Callable]:
    """
    Convenient decorator to register an action with the current Layers.
    This will get and restore attribute from function first argument.

    It will use the function name as the action name. We force the description
    to be given instead of function docstring for translation purpose.

    Parameters
    ----------
    keymapprovider : KeymapProvider
        class on which to register the keybindings - this will typically be
        the instance in focus that will handle the keyboard shortcut.
    description : str
        The description of the action, this will typically be translated and
        will be what will be used in tooltips.
    attribute_name : str
        The name of the attribute to be restored if key is hold over `get_settings().get_settings().application.hold_button_delay.
    shortcuts : str | List[str]
        Shortcut to bind by default to the action we are registering.

    Returns
    -------
    function:
        Actual decorator to apply to a function. Given decorator returns the
        function unmodified to allow decorator stacking.

    """

    def _handle(func: ty.Callable) -> ty.Callable:
        sig = inspect.signature(func)
        try:
            first_variable_name = next(iter(sig.parameters))
        except StopIteration as e:
            raise RuntimeError(
                "If actions has no arguments there is no way to know what to set the attribute to.",
            ) from e

        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            obj = args[0] if args else kwargs[first_variable_name]
            prev_mode = getattr(obj, attribute_name)
            func(*args, **kwargs)

            def _callback():
                setattr(obj, attribute_name, prev_mode)

            return _callback

        repeatable = False  # attribute actions are always non-repeatable
        register_layer_action(keymapprovider, description, repeatable, shortcuts)(_wrapper)
        return func

    return _handle
