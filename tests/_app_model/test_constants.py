from napari_plot._app_model.constants import MenuId


def test_menus():
    """make sure all menus start with napari/"""
    for menu in MenuId:
        assert menu.value.startswith("napari_plot/") or menu.value.startswith(
            "napari/"
        ), f"MenuId should start with 'napari/' or 'napari_plot/' {menu}"
