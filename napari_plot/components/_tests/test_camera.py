"""Tests for components/camera"""

from napari_plot.components.camera import Camera


def test_camera():
    """Test camera."""
    camera = Camera()
    assert camera.interactive
    assert camera.rect == (0, 0, 0, 0)
    assert camera.extent == (0, 0, 0, 0)
    assert camera.x_range is None
    assert camera.y_range is None

    x_range = (0, 5)
    camera.x_range = x_range
    assert camera.x_range == x_range
    assert camera.extent == (0, 0, 0, 0)
    assert camera.get_effective_extent() == (0, 5, 0, 0)
    camera.x_range = None
    assert camera.get_effective_extent() == (0, 0, 0, 0)

    y_range = (0, 5)
    camera.y_range = y_range
    assert camera.y_range == y_range
    assert camera.extent == (0, 0, 0, 0)
    assert camera.get_effective_extent() == (0, 0, 0, 5)
    camera.y_range = None
    assert camera.get_effective_extent() == (0, 0, 0, 0)

    extent = (5, 10, 5, 10)
    camera._extent = extent
    assert camera.get_effective_extent() == extent

    # from now on, extents are managed by the value of `_extent`
    camera.set_x_range(1, 3)
    assert camera.x_range == (1, 3)
    assert camera.get_effective_extent() == (1, 3, 5, 10)
    camera.set_x_range(1, None)
    assert camera.x_range == (1, 10)
    assert camera.get_effective_extent() == (1, 10, 5, 10)
    camera.set_x_range(None, 7)
    assert camera.x_range == (5, 7)
    assert camera.get_effective_extent() == (5, 7, 5, 10)
    camera.x_range = None  # reset effect x-range

    camera.set_y_range(1, 3)
    assert camera.y_range == (1, 3)
    assert camera.get_effective_extent() == (5, 10, 1, 3)
    camera.set_y_range(1, None)
    assert camera.y_range == (1, 10)
    assert camera.get_effective_extent() == (5, 10, 1, 10)
    camera.set_y_range(None, 7)
    assert camera.y_range == (5, 7)
    assert camera.get_effective_extent() == (5, 10, 5, 7)
