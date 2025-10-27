"""Action manger instance."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Callable

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


napari.utils.action_manager.Action = Action


action_manager = napari.utils.action_manager.ActionManager()
