from types import SimpleNamespace

import numpy as np
from vispy.geometry import Rect

from napari_plot._vispy.camera import VispyCamera
from napari_plot.components.axis import Axis


def test_transform_rect_for_log_axes() -> None:
    """Camera rectangles are transformed independently for each log axis."""
    camera = VispyCamera.__new__(VispyCamera)
    camera._viewer = SimpleNamespace(
        axis=Axis(x_scale="log", y_scale="linear")
    )
    data_rect = Rect(0.1, 2.0, 999.9, 3.0)

    display_rect = camera._transform_rect(data_rect, inverse=False)

    assert np.allclose(display_rect, (-1.0, 3.0, 2.0, 5.0))
    assert np.allclose(
        camera._transform_rect(display_rect, inverse=True),
        (0.1, 1000.0, 2.0, 5.0),
    )
