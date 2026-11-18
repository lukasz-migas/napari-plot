"""Color handling shared by every statistical plot."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

import numpy as np
from napari.utils.colormaps.standardize_color import transform_color

from napari_plot.stats._data import CategoricalData


def to_rgba(color: Any) -> np.ndarray:
    """Return one RGBA color."""
    return np.asarray(transform_color(color)[0], dtype=float)


def level_colors(levels: Sequence[Any], palette: Any = None, color: Any = None) -> dict[Any, np.ndarray]:
    """Map each level to an RGBA color.

    Parameters
    ----------
    levels : sequence
        Ordered levels to color.
    palette : str, sequence or dict, optional
        Any seaborn palette spec, or an explicit level -> color mapping.
    color : color, optional
        Single color used for every level when ``palette`` is not given.
    """
    from napari_plot.stats._seaborn import color_palette

    if isinstance(palette, Mapping):
        return {level: to_rgba(palette[level]) for level in levels}
    if palette is None and color is not None:
        return dict.fromkeys(levels, to_rgba(color))
    colors = color_palette(palette, n_colors=max(len(levels), 1))
    return {level: np.array([*rgb, 1.0]) for level, rgb in zip(levels, colors, strict=False)}


def categorical_color_fn(
    data: CategoricalData, palette: Any = None, color: Any = None
) -> Callable[[int, Any], np.ndarray]:
    """Return ``fn(category_index, hue_level) -> RGBA`` following seaborn's coloring rules.

    Hue levels get palette colors; without hue, categories are colored individually when a palette is given
    (or ``hue`` equals the category variable) and otherwise share one color.
    """
    if data.hue_levels is not None:
        colors = level_colors(data.hue_levels, palette, color)
        return lambda _index, hue: colors[hue]
    if data.color_by_category or palette is not None:
        colors = level_colors(range(len(data.categories)), palette, color)
        return lambda index, _hue: colors[index]
    single = to_rgba(color) if color is not None else level_colors([0])[0]
    return lambda _index, _hue: single


def colormap_from_mpl(cmap: Any) -> Any:
    """Convert a matplotlib colormap into a napari ``Colormap`` named after its colors (stable, unique)."""
    from hashlib import md5

    from napari.utils.colormaps import Colormap

    colors = np.asarray(cmap(np.linspace(0, 1, 256)), dtype=float)
    digest = md5(colors.tobytes(), usedforsecurity=False).hexdigest()[:8]
    return Colormap(colors, name=f"{getattr(cmap, 'name', 'stats')}_{digest}")
