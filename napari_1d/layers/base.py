"""Napari-1d base layer"""
from contextlib import contextmanager

import numpy as np
from napari.layers.base import Layer
from napari.utils.events import Event


class BaseLayer(Layer):
    """Base layer that overrides certain napari Layer characteristics."""

    _label: str = ""

    # Flag set to false to block thumbnail refresh
    _allow_thumbnail_update = True

    def __init__(
        self,
        data,
        *,
        # napari-1d parameters
        label="",
        # napari parameters
        name=None,
        metadata=None,
        scale=None,
        translate=None,
        rotate=None,
        shear=None,
        affine=None,
        opacity=1.0,
        blending="translucent",
        visible=True,
    ):
        super().__init__(
            data,
            ndim=2,
            name=name,
            metadata=metadata,
            scale=scale,
            translate=translate,
            rotate=rotate,
            shear=shear,
            affine=affine,
            opacity=opacity,
            blending=blending,
            visible=visible,
        )

        self.events.add(label=Event)
        self._label = label

    @property
    def data(self):
        """Get data."""
        raise NotImplementedError("Must implement method")

    @property
    def _extent_data(self) -> np.ndarray:
        raise NotImplementedError("Must implement method")

    def _get_state(self):
        raise NotImplementedError("Must implement method")

    def _set_view_slice(self):
        raise NotImplementedError("Must implement method")

    def _update_thumbnail(self):
        raise NotImplementedError("Must implement method")

    def _get_value(self, position):
        raise NotImplementedError("Must implement method")

    def _get_ndim(self):
        return 2

    @property
    def label(self) -> str:
        """Get label."""
        return self._label

    @label.setter
    def label(self, value: str):
        self._label = value
        self.events.label()

    def _emit_new_data(self):
        self._update_dims()
        self.events.data(value=self.data)
        self._set_editable()

    @contextmanager
    def block_thumbnail_update(self):
        """Use this context manager to block thumbnail updates"""
        self._allow_thumbnail_update = False
        yield
        self._allow_thumbnail_update = True
