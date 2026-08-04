"""Tests for interactions between custom and native napari layers."""

from napari import layers as napari_layers, types as napari_types

from napari_plot import layers as plot_layers


def test_custom_layer_registration_matches_napari_contract() -> None:
    """Every registered layer should expose the attributes napari expects."""
    custom_layers = (
        plot_layers.Centroids,
        plot_layers.InfLine,
        plot_layers.Line,
        plot_layers.MultiLine,
        plot_layers.Region,
        plot_layers.Scatter,
        plot_layers.Text,
    )

    for layer_type in custom_layers:
        type_name = layer_type.__name__.lower()
        title = type_name.title()
        assert type_name in napari_layers.NAMES
        assert getattr(napari_layers, title) is layer_type
        assert hasattr(napari_types, f"{title}Data")
