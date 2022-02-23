# napari-plot

[![License](https://img.shields.io/pypi/l/napari-1d.svg?color=green)](https://github.com/lukasz-migas/napari-1d/raw/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/napari-1d.svg?color=green)](https://pypi.org/project/napari-plot)
[![Python Version](https://img.shields.io/pypi/pyversions/napari-plot.svg?color=green)](https://python.org)
[![tests](https://github.com/lukasz-migas/napari-1d/workflows/tests/badge.svg)](https://github.com/lukasz-migas/napari-1d/actions)
[![codecov](https://codecov.io/gh/lukasz-migas/napari-1d/branch/main/graph/badge.svg)](https://codecov.io/gh/lukasz-migas/napari-1d)

Plugin providing support for 1d plotting in napari.

This plugin is in very early stages of development and many things are still in a state of disarray. New features and bug fixes
will be coming over the coming months. 

## Note

`napari-plot` provides several custom icons and stylesheets to take advantage of the `Qt` backend. Since it would be a bit busy to add multiple layer lists,
I opted to include a toolbar that quickly pulls the layer list whenever requested. Simple use the toolbar to access several commonly accessed elements.

## Usage

You can use `napari-plot` alongside `napari` where it is embedded as a dock widget. If using this option, controls are relegated to toolbar
where you can adjust layer properties like you would do in `napari`.

![embedded](https://github.com/lukasz-migas/napari-1d/blob/main/misc/embedded.png)

Or as a standalone app where only one-dimensional plotting is enabled. In this mode, controls take central stage and reflect `napari's` own
behaviour where layer controls are embedded in the main application.

![live-view](https://github.com/lukasz-migas/napari-1d/blob/main/misc/napariplot-live-line.gif)

## Roadmap:

This is only provisional list of features that I would like to see implemented. It barely scratches the surface of what plotting tool should cover so as soon as the basics are covered,
focus will be put towards adding more exotic features. If there are features that you certainly wish to be included,
please modify the list below or create a [new issue](https://github.com/lukasz-migas/napari-1d/issues/new)

- [ ] Support for new layer types. Layers are based on `napari's` `Layer`, albeit in a two-dimensional setting. Supported and planned layers:
  - [x] Line Layer - simple line plot.
  - [x] Scatter Layer - scatter plot (similar to `napari's Points` layer).
  - [x] Centroids/Segments Layer - horizontal or vertical line segments.
  - [x] InfLine Layer - infinite horizontal or vertical lines that span over very broad range. Useful for defining regions of interest.
  - [x] Region Layer - infinite horizontal or vertical rectangular boxes that span over very broad range. Useful for defining regions of interest.
  - [x] Shapes Layer - `napari's` own `Shapes` layer
  - [x] Points Layer - `napari's` own `Points` layer
  - [x] Multi-line Layer - more efficient implementation of `Line` layer when multiple lines are necessary. (TODO)
  - [ ] Bar - horizontal and vertical barchart (TODO)
- [x] Proper interactivity of each layer type (e.g. moving `Region` or `InfLine`, adding points, etc...)
- [ ] Intuitive interactivity. `napari-plot` will provide excellent level of interactivity with the plotted data. We plan to support several types of `Tools` that permit efficient interrogation of the data.
  We currently support three zoom modes and plan to add a couple other tools.
  - [x] Box-zoom - standard zooming rectangle. Simply `left-mouse + drag/release` in the canvas on region of interest
  - [x] Horizontal span - zoom-in only in the y-axis by `Ctrl + left-mouse + drag/release` in the canvas.
  - [x] Vertical span - span-in only in the x-axis by `Shift + left-mouse + drag/release` in the canvas.
  - [ ] Rectangle select - rectangle tool allowing sub-selection of data in the canvas. Similar to the `Box-zoom` but without the zooming part. (TODO)
  - [ ] Polygon select - polygon tool allowing sub-selection of data in the canvas. (TODO)
  - [ ] Lasso select - lasso tool allowing sub-selection of data in the canvas. (TODO)
- [ ] Interactive plot legend
- [ ] Customizable axis visuals.
  - [x] Plot axis enabling customization of tick/label size and color
  - [ ] Support for non-linear scale

----------------------------------

This [napari] plugin was generated with [Cookiecutter] using with [@napari]'s [cookiecutter-napari-plugin] template.

<!--
Don't miss the full getting started guide to set up your new package:
https://github.com/napari/cookiecutter-napari-plugin#getting-started

and review the napari docs for plugin developers:
https://napari.org/docs/plugins/index.html
-->

## Installation

You can install `napari-plot` directly from PyPI via:

```python
pip install napari-plot
```

or from the git repo:

```python
git clone https://github.com/lukasz-migas/napari-1d.git
cd napari-1d
pip install -e '.[all]'
```

## Contributing

Contributions are very welcome. Tests can be run with [tox], please ensure
the coverage at least stays the same before you submit a pull request.

## License

Distributed under the terms of the [BSD-3] license,
"napari-plot" is free and open source software

## Issues

If you encounter any problems, please [file an issue] along with a detailed description.

[napari]: https://github.com/napari/napari
[Cookiecutter]: https://github.com/audreyr/cookiecutter
[@napari]: https://github.com/napari
[BSD-3]: http://opensource.org/licenses/BSD-3-Clause
[Apache Software License 2.0]: http://www.apache.org/licenses/LICENSE-2.0
[cookiecutter-napari-plugin]: https://github.com/napari/cookiecutter-napari-plugin
[file an issue]: https://github.com/lukasz-migas/napari-1d/issues
[napari]: https://github.com/napari/napari
[tox]: https://tox.readthedocs.io/en/latest/
[pip]: https://pypi.org/project/pip/
[PyPI]: https://pypi.org/
