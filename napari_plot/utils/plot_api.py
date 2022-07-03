"""Functions related to the plot API."""
import typing as ty
import warnings

import numpy as np
from napari.layers.points._points_constants import SYMBOL_ALIAS, Symbol

from .exception import NotSupportedWarning


def parse_plot(x, y, fmt, **kwargs) -> ty.Tuple[str, ty.Dict]:
    """Parse plot data and return iterable with appropriate structure to easily create line/scatter layers.

    The `args` expects certain arguments which can be:
        x, y, fmt
        y, fmt
        y
    where x and y are arrays and fmt is string that determines color/shape of the scatter points
    """
    exclude = ["ls", "linestyle"]
    sanitize_kwargs(exclude, kwargs)
    replace_kwargs(kwargs)

    y = np.asarray(y)
    if x is not None:
        x, y = y, x
    if x is None:
        x = np.arange(len(y))
    kwargs.update(data=np.c_[x, y])

    marker = None
    if fmt is not None:
        marker, color = _parse_scatter_fmt(fmt, **kwargs)
        if marker is not None:
            kwargs.update(face_color=color, symbol=marker)
        else:
            kwargs.update(color=color)
    layer_type = "line" if marker is None else "scatter"
    return layer_type, kwargs


def _parse_scatter_fmt(fmt: str, **kwargs):
    """Parse scatter format so it can be understood by the Scatter layer type.

    Rather than reinventing the wheel, we are using matplotlib's parser for the purpose of understanding the format.
    Of course, napari-plot does not support dotted or dashed lines so that information is ignored.
    """
    from matplotlib.axes._base import _process_plot_format

    if not isinstance(fmt, str):
        raise ValueError(f"Format should be a string and not '{type(fmt)}'.")
    _, marker, color = _process_plot_format(fmt)
    marker = SYMBOL_ALIAS.get(marker)
    if marker:
        marker = Symbol(marker)
    return marker, color


def parse_scatter(x, y, s, c, marker, alpha, **kwargs) -> ty.Dict:
    """Parse scatter data nad parameters."""
    x, y = np.asarray(x), np.asarray(y)
    # parse size
    s = kwargs.pop("size", s)
    s = s if s is not None else 5  # set to default if one was not provided
    # parse color
    c = kwargs.pop("face_color", c)
    c = c if c is not None else np.array((1.0, 1.0, 1.0, 1.0))  # set to default if one was not provided
    # parse symbol
    marker = kwargs.pop("symbol", marker)
    marker = marker if marker is not None else "o"
    marker = SYMBOL_ALIAS.get(marker)
    marker = Symbol(marker)
    # parse opacity
    alpha = kwargs.pop("opacity", alpha)
    alpha = alpha if not None else 1.0

    kwargs.update(data=np.c_[x, y], size=s, face_color=c, symbol=marker, opacity=alpha)
    return kwargs


def parse_bar(x, height, width, bottom, align, **kwargs) -> ty.Tuple[ty.Dict, ty.Dict]:
    """Parse barchart data and parameters and return kwargs to be consumed by the 'Shapes' layer type."""
    # these are some of the kwargs that can be supplied to matplotlib but we don't accept them
    exclude = ["log", "label", "tick_label", "capsize"]
    sanitize_kwargs(exclude, kwargs)

    # bar chart
    opacity = kwargs.pop("alpha", None)
    opacity = kwargs.pop("opacity", opacity)
    opacity = opacity if opacity is not None else 1.0

    color = kwargs.pop("color", None)
    color = kwargs.pop("face_color", color)
    color = color if color is not None else np.array((1.0, 1.0, 1.0, 1.0))

    line_width = kwargs.pop("linewidth", None)
    orientation = kwargs.pop("orientation", "vertical").lower()
    check_in_list(orientation, ["vertical", "horizontal"])

    y = bottom
    if orientation == "vertical":
        y = 0 if y is None else y
    else:
        x = 0 if x is None else x

    # normalize length of input arrays
    x, height, width, y, line_width = np.broadcast_arrays(np.atleast_1d(x), height, width, y, line_width)
    # fix alignment
    check_in_list(align, ["center", "edge"])
    if align == "center":
        if orientation == "vertical":
            try:
                left = x - width / 2
            except TypeError as e:
                raise TypeError(
                    f"The dtypes of parameters x ({x.dtype}) and width ({width.dtype}) are incompatible"
                ) from e
            bottom = y
        else:
            try:
                bottom = y - height / 2
            except TypeError as e:
                raise TypeError(
                    f"The dtypes of parameters y ( {y.dtype})  and height ({height.dtype})  are incompatible"
                ) from e
            left = x
    else:
        left = x
        bottom = y
    # create rectangles that can be understood by the 'Shapes' layer
    data = []
    for _left, _bottom, _width, _height in zip(left, bottom, width, height):
        corner = np.asarray([_bottom, _left])  # y, x
        size_h = np.asarray([0, _width])
        size_v = np.asarray([_height, 0])
        data.append(([corner, corner + size_v, corner + size_h + size_v, corner + size_h], "rectangle"))
    # edges don't look right and they won't do unless we change the Shapes visual to not use vertices...
    kwargs.update(data=data, edge_width=0, face_color=color, opacity=opacity)

    # error bars
    error_x = kwargs.pop("xerr", None)
    error_y = kwargs.pop("yerr", None)
    error_kw = {}
    if error_x is not None or error_y is not None:
        error_kw = kwargs.pop("error_kw", {})
        error_color = kwargs.pop("ecolor", "red")
        error_kw.update(color=error_color)

        if orientation == "vertical":
            ex = left + 0.5 * width
            ey = bottom + height
        else:
            ex = left + width
            ey = bottom + 0.5 * height
        error_x = 0 if error_x is None else error_x
        error_y = 0 if error_y is None else error_y
        error_data = np.c_[ex - error_x, ex + error_x, ey - error_y, ey + error_y]
        error_kw.update(data=error_data)
    return kwargs, error_kw


def parse_span(val_min, val_max, ax_min, ax_max, orientation, **kwargs):
    """Parse parameters for span."""
    if ax_min != 0 or ax_max != 1:
        warnings.warn(
            "napari-plot does not support specifying the 'axis min/max' and spans will occupy the entire axis",
            NotSupportedWarning,
        )
    check_in_list(orientation, ["vertical", "horizontal"])

    data = ("vertical", (val_min, val_max)) if orientation == "vertical" else ("horizontal", (val_min, val_max))
    kwargs.update(data=data)
    return kwargs


def parse_axline(val, ax_min, ax_max, orientation, **kwargs):
    """Parse parameters for infinite lines"""
    exclude = ["ls", "linestyle"]
    sanitize_kwargs(exclude, kwargs)
    replace_kwargs(kwargs)

    if ax_min != 0 or ax_max != 1:
        warnings.warn(
            "napari-plot does not support specifying the 'axis min/max' and spans will occupy the entire axis",
            NotSupportedWarning,
        )
    check_in_list(orientation, ["vertical", "horizontal"])

    data = (val, "vertical") if orientation == "vertical" else (val, "horizontal")
    kwargs.update(data=data)
    return kwargs


def check_in_list(value, iterable):
    """Check whether value is in the list and if not, throw ValueError exception."""
    if value not in iterable:
        options = ", ".join(iterable)
        raise ValueError(f"Specified value is not in found in the list. value='{value}'; available options='{options}'")


def sanitize_kwargs(exclude: ty.Iterable[str], kwargs: ty.Dict):
    """Sanitize kwargs by removing keys which are not supported."""
    for exc in exclude:
        kwargs.pop(exc, None)
    return kwargs


# mapping between matplotlib -> napari-plot
MAPPING = {"width": ("lw", "linewidth"), "opacity": ("alpha",)}


def replace_kwargs(kwargs: ty.Dict):
    """Replace common matplotlib kwargs."""
    for nap_kw, mpl_kws in MAPPING.items():
        for mpl_kw in mpl_kws:
            if mpl_kw in kwargs:
                kwargs[nap_kw] = kwargs.pop(mpl_kw)


# def parse_common_mpl(kwargs: ty.Dict):
#     """Parse common arguments"""
#     opacity = kwargs.pop("alpha", None)
#     opacity = kwargs.pop("opacity", opacity)
#     opacity = opacity if opacity is not None else 1.0
