import numpy as np
from napari.layers.points._points_constants import SYMBOL_ALIAS, Symbol


def coerce_symbols(array: np.ndarray) -> np.ndarray:
    """
    Parse an array of symbols and convert it to the correct strings.

    Ensures that all strings are valid symbols and converts aliases.

    Parameters
    ----------
    array : np.ndarray
        Array of strings matching Symbol values.
    """
    # dtype has to be object, otherwise np.vectorize will cut it down to `U(N)`,
    # where N is the biggest string currently in the array.
    array = array.astype(object, copy=True)
    for k, v in SYMBOL_ALIAS.items():
        array[(array == k) | (array == k.upper())] = v
    # otypes necessary for empty arrays
    return np.vectorize(Symbol, otypes=[object])(array)
