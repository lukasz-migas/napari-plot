"""Test utilities."""
from napari_plot.utils.color import DEFAULT_CYCLE


def test_default():
    old_color = None
    # make sure colors are not repeated
    for i in range(DEFAULT_CYCLE.count):
        color = DEFAULT_CYCLE.next()
        assert color != old_color
        old_color = color
