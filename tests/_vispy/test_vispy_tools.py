from napari_plot._vispy.tools.polygon import VispyPolygonVisual


def test_vispy_text_visual(make_napari_plot_viewer):
    viewer = make_napari_plot_viewer()
    qt_widget = viewer.window._qt_viewer
    assert viewer.drag_tool is not None
    assert qt_widget.canvas.tool is not None

    # change tool
    viewer.drag_tool.active = "polygon"
    assert isinstance(qt_widget.canvas.tool.tool, VispyPolygonVisual)
    viewer.drag_tool.active = "none"
    assert qt_widget.canvas.tool.tool is None
    viewer.drag_tool.active = "box"
    assert isinstance(qt_widget.canvas.tool.tool, VispyPolygonVisual)
