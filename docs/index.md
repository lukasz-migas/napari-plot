# napari-plot

## Vispy-based plot viewer for Python

napari-plot is based and inspired by the highly popular [napari](https://napari.org) project. The aim to create a fast, interactive
visualisation environment for Python that is compatible with napari but can also stand on its own two legs.
**napari-plot** is built on top of `Qt` (for the GUI), `vispy` (for performant GPU-based rendering), the scientific Python stack
(`numpy`, `scipy`) and `napari` itself (for e.g. layer system).

`napari-plot` is developed in the open and as you can imagine, there are many rough edges that need sanding! We are hoping
to add essential functionality first and focus on fixing what we break along the way. Contributions to the project
are absolutely, definitely welcome! Please see our [GitHub repository](https://github/lukasz-migas/napari-plot)

## Installation

### From pip, with "batteries included"

`napari-plot` can be installed on most Windows, Linux and macOS systems with Python 3.8-3.10 using pip:

```
pip install "napari-plot[all]"
```

### From conda

```
conda install -c conda-forge napari-plot
```

### Current development branch from GitHub

To install the current `main` branch on `GitHub` (which will be ahead of the latest release on PyPI)

```
pip install "git+https://github.com/lukasz-migas/napari-plot.git#egg=napari_plot[all]"
```

## Getting started

TODO

## Features

TODO