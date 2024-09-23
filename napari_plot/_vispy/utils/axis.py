"""Utils"""

import numpy as np


def tick_formatter(value: float) -> str:
    """Format tick value"""
    value = float(value)
    exp_value = np.round(np.log10(abs(value)))
    if np.isinf(exp_value):
        exp_value = 1
    if exp_value < 3:
        if abs(value) <= 1:
            return f"{value:.2G}"
        elif abs(value) <= 1e3:
            if value.is_integer():
                return f"{value:.0F}"
            return f"{value:.1F}"
    elif exp_value < 6:
        return f"{value / 1e3:.1f}k"
    elif exp_value < 9:
        return f"{value / 1e6:.1f}M"
    elif exp_value < 12:
        return f"{value / 1e9:.1f}B"
    elif exp_value < 16:
        return f"{value / 1e12:.1f}T"
