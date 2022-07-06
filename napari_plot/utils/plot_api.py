"""Functions related to the plot API."""
import typing as ty
import warnings
from numbers import Number

import numpy as np
from napari.layers.points._points_constants import SYMBOL_ALIAS, Symbol

from .color import DEFAULT_CYCLE
from .exception import NotSupportedWarning

# mapping between matplotlib -> napari-plot
MAPPING = {"width": ("lw", "linewidth"), "opacity": ("alpha",), "colormap": ("cmap",)}


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
    preset_layer_name(layer_type.capitalize(), kwargs)
    return layer_type, kwargs


def parse_scatter(x, y, s, c, marker, alpha, **kwargs) -> ty.Dict:
    """Parse scatter data nad parameters."""
    preset_layer_name("Scatter", kwargs)

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

    kwargs.update(data=np.c_[y, x], size=s, face_color=c, symbol=marker, opacity=alpha)
    return kwargs


def parse_bar(x, height, width, bottom, align, **kwargs) -> ty.Tuple[ty.Dict, ty.Dict]:
    """Parse barchart data and parameters and return kwargs to be consumed by the 'Shapes' layer type."""
    # these are some of the kwargs that can be supplied to matplotlib but we don't accept them
    exclude = ["log", "label", "tick_label", "capsize"]
    sanitize_kwargs(exclude, kwargs)
    preset_layer_name("Barchart", kwargs)

    # bar chart
    opacity = kwargs.pop("alpha", None)
    opacity = kwargs.pop("opacity", opacity)
    opacity = opacity if opacity is not None else 1.0

    color = kwargs.pop("color", None)
    color = kwargs.pop("face_color", color)
    color = color if color is not None else np.array((1.0, 1.0, 1.0, 1.0))

    line_width = kwargs.pop("linewidth", None)
    orientation = kwargs.pop("orientation", "vertical").lower()
    check_in_list(["vertical", "horizontal"], orientation=orientation)
    check_in_list(["center", "edge"], align=align)

    y = bottom
    if orientation == "vertical":
        y = 0 if y is None else y
    else:
        x = 0 if x is None else x

    # normalize length of input arrays
    x, height, width, y, line_width = np.broadcast_arrays(np.atleast_1d(x), height, width, y, line_width)
    # fix alignment
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
        preset_layer_name("Barchart-errors", error_kw)
    return kwargs, error_kw


def parse_span(val_min, val_max, ax_min, ax_max, orientation, **kwargs):
    """Parse parameters for span."""
    preset_layer_name("Span", kwargs)
    if ax_min != 0 or ax_max != 1:
        warnings.warn(
            "napari-plot does not support specifying the 'axis min/max' and spans will occupy the entire axis",
            NotSupportedWarning,
        )
    check_in_list(["vertical", "horizontal"], orientation=orientation)

    data = ((val_min, val_max), "vertical") if orientation == "vertical" else ((val_min, val_max), "horizontal")
    kwargs.update(data=data)
    return kwargs


def parse_axline(val, ax_min, ax_max, orientation, **kwargs):
    """Parse parameters for infinite lines"""
    exclude = ["ls", "linestyle"]
    sanitize_kwargs(exclude, kwargs)
    replace_kwargs(kwargs)
    preset_layer_name("InfLine", kwargs)

    if ax_min != 0 or ax_max != 1:
        warnings.warn(
            "napari-plot does not support specifying the 'axis min/max' and spans will occupy the entire axis",
            NotSupportedWarning,
        )
    check_in_list(["vertical", "horizontal"], orientation=orientation)

    data = (val, "vertical") if orientation == "vertical" else (val, "horizontal")
    kwargs.update(data=data)
    return kwargs


def parse_hist(
    x,
    bins=None,
    bin_range=None,
    density=False,
    weights=None,
    cumulative=False,
    bottom=None,
    histtype="bar",
    align="mid",
    orientation="vertical",
    rwidth=None,
    log=False,
    color=None,
    label=None,
    stacked=False,
    **kwargs,
):
    """Parse histogram parameters."""
    from matplotlib import cbook

    preset_layer_name("Histogram", kwargs)

    if np.isscalar(x):
        x = [x]

    if bins is None:
        bins = 10

    # Validate string inputs here to avoid cluttering subsequent code.
    replace_kwargs(kwargs)
    check_in_list(["bar", "barstacked", "step", "stepfilled"], histtype=histtype)
    check_in_list(["left", "mid", "right"], align=align)
    check_in_list(["horizontal", "vertical"], orientation=orientation)

    if histtype.startswith("step"):
        raise NotImplementedError("Must implement method")

    if histtype == "barstacked" and not stacked:
        stacked = True

    # Massage 'x' for processing.
    x = cbook._reshape_2D(x, "x")
    nx = len(x)  # number of datasets

    # We need to do to 'weights' what was done to 'x'
    if weights is not None:
        w = cbook._reshape_2D(weights, "weights")
    else:
        w = [None] * nx

    if len(w) != nx:
        raise ValueError("weights should have the same shape as x")

    input_empty = True
    for xi, wi in zip(x, w):
        len_xi = len(xi)
        if wi is not None and len(wi) != len_xi:
            raise ValueError("weights should have the same shape as x")
        if len_xi:
            input_empty = False

    if color is None:
        color = [DEFAULT_CYCLE() for _ in range(nx)]
    hist_kwargs = dict()

    # if the bin_range is not given, compute without nan numpy
    # does not do this for us when guessing the range (but will
    # happily ignore nans when computing the histogram).
    if bin_range is None:
        xmin = np.inf
        xmax = -np.inf
        for xi in x:
            if len(xi):
                # python's min/max ignore nan,
                # np.minnan returns nan for all nan input
                xmin = min(xmin, np.nanmin(xi))
                xmax = max(xmax, np.nanmax(xi))
        if xmin <= xmax:  # Only happens if we have seen a finite value.
            bin_range = (xmin, xmax)

    # If bins are not specified either explicitly or via range,
    # we need to figure out the range required for all datasets,
    # and supply that to np.histogram.
    if not input_empty and len(x) > 1:
        if weights is not None:
            _w = np.concatenate(w)
        else:
            _w = None
        bins = np.histogram_bin_edges(np.concatenate(x), bins, bin_range, _w)
    else:
        hist_kwargs["range"] = bin_range

    density = bool(density)
    if density and not stacked:
        hist_kwargs["density"] = density

    # List to store all the top coordinates of the histograms
    tops = []  # Will have shape (n_datasets, n_bins).
    # Loop through datasets
    for i in range(nx):
        # this will automatically overwrite bins,
        # so that each histogram uses the same bins
        m, bins = np.histogram(x[i], bins, weights=w[i], **hist_kwargs)
        tops.append(m)
    tops = np.array(tops, float)  # causes problems later if it's an int
    if stacked:
        tops = tops.cumsum(axis=0)
        # If a stacked density plot, normalize so the area of all the
        # stacked histograms together is 1
        if density:
            tops = (tops / np.diff(bins)) / tops[-1].sum()
    if cumulative:
        slc = slice(None)
        if isinstance(cumulative, Number) and cumulative < 0:
            slc = slice(None, None, -1)
        if density:
            tops = (tops * np.diff(bins))[:, slc].cumsum(axis=1)[:, slc]
        else:
            tops = tops[:, slc].cumsum(axis=1)[:, slc]

    layer_type = None
    layer_kwargs = []
    if histtype.startswith("bar"):
        tot_width = np.diff(bins)
        if rwidth is not None:
            dr = np.clip(rwidth, 0, 1)
        elif len(tops) > 1:  # and ((not stacked): # or rcParams["_internal.classic_mode"]):
            dr = 0.8
        else:
            dr = 1.0

        if histtype == "bar" and not stacked:
            width = dr * tot_width / nx
            dw = width
            bar_offset = -0.5 * dr * tot_width * (1 - 1 / nx)
        elif histtype == "barstacked" or stacked:
            width = dr * tot_width
            bar_offset, dw = 0.0, 0.0

        if align == "mid":
            bar_offset += 0.5 * tot_width
        elif align == "right":
            bar_offset += tot_width

        if orientation == "horizontal":
            bottom_kwarg = "left"
        else:
            bottom_kwarg = "bottom"

        for m, c in zip(tops, color):
            if bottom is None:
                bottom = np.zeros(len(m))
            if stacked:
                height = m - bottom
            else:
                height = m

            _bar_kwargs = (
                (bins[:-1] + bar_offset, height, width),
                {"align": "center", "log": log, "face_color": c, bottom_kwarg: bottom, **kwargs},
            )
            layer_kwargs.append(_bar_kwargs)
            if stacked:
                bottom = m
            bar_offset += dw
        layer_type = "barh" if orientation == "horizontal" else "bar"
    elif histtype.startswith("step"):
        raise NotImplementedError("Must implement method")
        # these define the perimeter of the polygon
        # x = np.zeros(4 * len(bins) - 3)
        # y = np.zeros(4 * len(bins) - 3)
        #
        # x[0 : 2 * len(bins) - 1 : 2], x[1 : 2 * len(bins) - 1 : 2] = bins, bins[:-1]
        # x[2 * len(bins) - 1 :] = x[1 : 2 * len(bins) - 1][::-1]
        #
        # if bottom is None:
        #     bottom = 0
        #
        # y[1 : 2 * len(bins) - 1 : 2] = y[2 : 2 * len(bins) : 2] = bottom
        # y[2 * len(bins) - 1 :] = y[1 : 2 * len(bins) - 1][::-1]
        #
        # if align == "left":
        #     x -= 0.5 * (bins[1] - bins[0])
        # elif align == "right":
        #     x += 0.5 * (bins[1] - bins[0])
        #
        # # If fill kwarg is set, it will be passed to the patch collection,
        # # overriding this
        # fill = histtype == "stepfilled"
        #
        # xvals, yvals = [], []
        # for m in tops:
        #     if stacked:
        #         # top of the previous polygon becomes the bottom
        #         y[2 * len(bins) - 1 :] = y[1 : 2 * len(bins) - 1][::-1]
        #     # set the top of this polygon
        #     y[1 : 2 * len(bins) - 1 : 2] = y[2 : 2 * len(bins) : 2] = m + bottom
        #
        #     # The starting point of the polygon has not yet been
        #     # updated. So far only the endpoint was adjusted. This
        #     # assignment closes the polygon. The redundant endpoint is
        #     # later discarded (for step and stepfilled).
        #     y[0] = y[-1]
        #
        #     if orientation == "horizontal":
        #         xvals.append(y.copy())
        #         yvals.append(x.copy())
        #     else:
        #         xvals.append(x.copy())
        #         yvals.append(y.copy())
        #
        # # stepfill is closed, step is not
        # split = -1 if fill else 2 * len(bins)
        # add patches in reverse order so that when stacking,
        # items lower in the stack are plotted on top of
        # items higher in the stack
        # for x, y, c in reversed(list(zip(xvals, yvals, color))):
        #     _
        #     patches.append(
        #         self.fill(
        #             x[:split],
        #             y[:split],
        #             closed=True if fill else None,
        #             facecolor=c,
        #             edgecolor=None if fill else c,
        #             fill=fill if fill else None,
        #             zorder=None if fill else mlines.Line2D.zorder,
        #         )
        #     )
        # for patch_list in patches:
        #     for patch in patch_list:
        #         if orientation == "vertical":
        #             patch.sticky_edges.y.append(0)
        #         elif orientation == "horizontal":
        #             patch.sticky_edges.x.append(0)

    if nx == 1:
        return tops[0], bins, layer_type, layer_kwargs
    return tops, bins, layer_type, layer_kwargs


def parse_hist2d(
    x, y, bins=10, bin_range=None, density=False, weights=None, cmin=None, cmax=None, **kwargs
) -> ty.Tuple[ty.Dict, np.ndarray, np.ndarray]:
    """Parse parameters for hist2d plot."""
    replace_kwargs(kwargs)
    preset_layer_name("Histogram (2D)", kwargs)

    # calculate histogram data
    h, xedges, yedges = np.histogram2d(x, y, bins=bins, range=bin_range, density=density, weights=weights)
    if cmin is not None:
        h[h < cmin] = None
    if cmax is not None:
        h[h > cmax] = None

    # calculate scale
    scale_y = yedges[1] - yedges[0]
    scale_x = xedges[1] - xedges[0]

    return (
        {
            "data": h.T,
            "scale": (scale_y, scale_x),
            "translate": (yedges[0], xedges[0]),
            **kwargs,
        },
        xedges,
        yedges,
    )


def check_in_list(_values, *, _print_supported_values=True, **kwargs):
    """
    For each *key, value* pair in *kwargs*, check that *value* is in *_values*.

    Parameters
    ----------
    _values : iterable
        Sequence of values to check on.
    _print_supported_values : bool, default: True
        Whether to print *_values* when raising ValueError.
    **kwargs : dict
        *key, value* pairs as keyword arguments to find in *_values*.

    Raises
    ------
    ValueError
        If any *value* in *kwargs* is not found in *_values*.

    Examples
    --------
    >>> check_in_list(["foo", "bar"], arg=arg, other_arg=other_arg)
    """
    values = _values
    for key, val in kwargs.items():
        if val not in values:
            msg = f"{val!r} is not a valid value for {key}"
            if _print_supported_values:
                msg += f"; supported values are {', '.join(map(repr, values))}"
            raise ValueError(msg)


def preset_layer_name(default: str, kwargs: ty.Dict):
    """Set layer name based on a default."""
    name = kwargs.pop("name", None)
    name = kwargs.pop("label", name) or default
    kwargs["name"] = name


def sanitize_kwargs(exclude: ty.Iterable[str], kwargs: ty.Dict):
    """Sanitize kwargs by removing keys which are not supported."""
    for exc in exclude:
        kwargs.pop(exc, None)
    return kwargs


def replace_kwargs(kwargs: ty.Dict):
    """Replace common matplotlib kwargs."""
    for nap_kw, mpl_kws in MAPPING.items():
        for mpl_kw in mpl_kws:
            if mpl_kw in kwargs:
                kwargs[nap_kw] = kwargs.pop(mpl_kw)
