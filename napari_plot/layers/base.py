"""Napari-plot base layer"""

import typing as ty
import warnings
from contextlib import contextmanager

import numpy as np
from napari.layers.base import ActionType, Layer, _LayerSlicingState
from napari.types import LayerDataType
from napari.utils.events import EmitterGroup


def update_layer_attributes(layer: Layer, throw_exception: bool = True, **kwargs: ty.Any) -> None:
    """Update attributes on the layer."""
    for attr, value in kwargs.items():
        if not hasattr(layer, attr):
            if throw_exception:
                raise AttributeError(f"'{layer.__class__.__name__}' has no attribute '{attr}'")
            continue
        try:
            setattr(layer, attr, value)
        except (AttributeError, ValueError):
            if throw_exception:
                raise


class LayerMixin:
    """Mixin class."""

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

    def _emit_new_data(self, action_type: ActionType = ActionType.CHANGING):
        self._update_dims()
        self.events.data(value=self.data, action=action_type)
        self._on_editable_changed()

    @contextmanager
    def block_thumbnail_update(self):
        """Use this context manager to block thumbnail updates"""
        self._allow_thumbnail_update = False
        yield
        self._allow_thumbnail_update = True

    def update_attributes(self, throw_exception: bool = True, **kwargs):
        """Update attributes on the layer."""
        update_layer_attributes(self, throw_exception=throw_exception, **kwargs)

    def _get_mask_from_path(self, vertices, as_indices: bool = False):
        """Return data contained for specified vertices. Only certain layers implement this."""


class _BaseLayerSlicingState(_LayerSlicingState):
    """Generic layer-slicing state for napari-plot layers.

    napari's built-in layers (e.g. Points, Image) each define their own `_LayerSlicingState`
    subclass with a dedicated slice-request/response pipeline to support multiscale data and
    async slicing. napari-plot layers are simple, non-multiscale, 2D-only layers, so instead
    of replicating that machinery we just delegate straight to the layer's own
    `_set_view_slice` implementation.
    """

    layer: "BaseLayer"

    def _set_view_slice(self) -> None:
        self.layer._set_view_slice()


class BaseLayer(LayerMixin, Layer):
    """Base layer that overrides certain napari Layer characteristics."""

    def __init__(
        self,
        data,
        *,
        # napari parameters
        axis_labels=None,
        name=None,
        metadata=None,
        scale=None,
        translate=None,
        rotate=None,
        shear=None,
        affine=None,
        opacity=1.0,
        blending="translucent",
        experimental_clipping_planes=None,
        projection_mode="none",
        units=None,
        visible=True,
    ):
        Layer.__init__(
            self,
            data,
            ndim=2,
            axis_labels=axis_labels,
            name=name,
            metadata=metadata,
            scale=scale,
            translate=translate,
            rotate=rotate,
            shear=shear,
            affine=affine,
            opacity=opacity,
            blending=blending,
            experimental_clipping_planes=experimental_clipping_planes,
            projection_mode=projection_mode,
            units=units,
            visible=visible,
        )

    def _update_draw(self, scale_factor, corner_pixels_displayed, shape_threshold):
        """Update draw."""
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", "invalid value encountered in cast")
            super()._update_draw(scale_factor, corner_pixels_displayed, shape_threshold)

    def _get_layer_slicing_state(self, data: LayerDataType, cache: bool) -> _BaseLayerSlicingState:
        return _BaseLayerSlicingState(layer=self, data=data, cache=cache)
