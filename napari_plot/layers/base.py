"""Napari-plot base layer"""
import warnings
import typing as ty
from contextlib import contextmanager

import numpy as np
from napari.layers.base import Layer
from napari.utils.events import EmitterGroup, Event


class LayerMixin:
    """Mixin class."""

    _label: str = ""

    # Set flag to 'False' to disable thumbnail update
    _allow_thumbnail_update = True
    events: EmitterGroup
    _update_dims: ty.Callable
    _update_draw: ty.Callable

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

    def _emit_new_data(self):
        self._update_dims()
        self.events.data(value=self.data)
        self._on_editable_changed()

    @contextmanager
    def block_thumbnail_update(self):
        """Use this context manager to block thumbnail updates"""
        self._allow_thumbnail_update = False
        yield
        self._allow_thumbnail_update = True

    def update_attributes(self, throw_exception: bool = True, **kwargs):
        """Update attributes on the layer."""
        for attr, value in kwargs.items():
            if not hasattr(self, attr):
                if throw_exception:
                    raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{attr}'")
                else:
                    continue
            try:
                setattr(self, attr, value)
            except (AttributeError, ValueError) as err:
                if throw_exception:
                    raise err

    def _get_mask_from_path(self, vertices, as_indices: bool = False):
        """Return data contained for specified vertices. Only certain layers implement this."""


class BaseLayer(LayerMixin, Layer):
    """Base layer that overrides certain napari Layer characteristics."""

    def __init__(
        self,
        data,
        *,
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
        Layer.__init__(
            self,
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
        self.events.add()

    def _update_draw(self, scale_factor, corner_pixels_displayed, shape_threshold):
        """Update draw."""
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", "invalid value encountered in cast")
            super()._update_draw(scale_factor, corner_pixels_displayed, shape_threshold)
