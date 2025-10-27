from napari_plot.layers.region._region_utils import preprocess_box


def test_preprocess_box():
    data = (0, 100, 50, 250)  # xmin, xmax, ymin, ymax
    box = preprocess_box(data)
    assert len(box) == 2
    assert len(box[0]) == len(box[1]) == 2
    assert isinstance(box, list)
    assert box[0][0] == data[2]
    assert box[0][1] == data[0]
    assert box[1][0] == data[3]
    assert box[1][1] == data[1]
