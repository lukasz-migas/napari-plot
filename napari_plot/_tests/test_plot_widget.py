# import napari_plot
# import pytest
#
# # this is your plugin name declared in your napari.plugins entry point
# PLUGIN_NAME = "napari_plot"
# # the name of your widget(s)
# WIDGET_NAMES = ["NapariPlotWidget"]
#
#
# @pytest.mark.parametrize("widget_name", WIDGET_NAMES)
# def test_add_dock_widget(widget_name, make_napari_viewer, napari_plugin_manager):
#     napari_plugin_manager.register(napari_plot, name=PLUGIN_NAME)
#     viewer = make_napari_viewer()
#     num_dw = len(viewer.window._dock_widgets)
#     viewer.window.add_plugin_dock_widget(
#         plugin_name=PLUGIN_NAME, widget_name=widget_name
#     )
#     assert len(viewer.window._dock_widgets) == num_dw + 1
#
# #     # make sure console is not available
# #     assert viewer.window._dock_widgets[-1].qt_viewer.dockConsole is None
# #     assert viewer.window._dock_widgets[-1].qt_viewer.console is None
