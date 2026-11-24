"""Action manger instance."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING

import napari.utils.action_manager

if TYPE_CHECKING:
    from concurrent.futures import Future

    from napari.utils.key_bindings import KeymapProvider


@dataclass
class Action:
    command: Callable
    description: str
    keymapprovider: KeymapProvider  # subclassclass or instance of a subclass
    repeatable: bool = False

    @cached_property
    def injected(self) -> Callable[..., Future]:
        """command with napari objects injected.

        This will inject things like the current viewer, or currently selected
        layer into the commands.  See :func:`inject_napari_dependencies` for
        details.
        """
        from napari_plot._app_model import get_app_model

        return get_app_model().injection_store.inject(self.command)


class ActionManager(napari.utils.action_manager.ActionManager):
    """Action manager whose actions inject napari-plot objects.

    napari's manager builds its own ``Action`` class, which injects from napari's app-model. This subclass
    keeps napari-plot actions on napari-plot's app-model without patching napari's module.
    """

    def register_action(
        self,
        name: str,
        command: Callable,
        description: str,
        keymapprovider: KeymapProvider | None,
        repeatable: bool = False,
    ) -> None:
        """Register an action and bind any shortcuts that were declared before it."""
        self._validate_action_name(name)
        self._actions[name] = Action(command, description, keymapprovider, repeatable)
        if keymapprovider:
            self._update_shortcut_bindings(name)


action_manager = ActionManager()
