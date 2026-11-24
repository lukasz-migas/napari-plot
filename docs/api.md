# API reference

Class signatures, methods, and docstrings are rendered from the Python source. The layer and stats sections follow their modules' `__all__` exports, so new public classes and plotting functions appear here on the next docs build.

## Viewer and layout classes

::: napari_plot.viewer.Viewer
    options:
      members: true
      inherited_members: false
      filters: ["!^_"]

::: napari_plot.components.viewer_model.ViewerModel
    options:
      members: true
      filters: ["!^_"]

::: napari_plot.components.joint_grid.JointGrid
    options:
      members: true
      filters: ["!^_"]

## napari widgets

::: napari_plot._plot_widget.NapariPlotWidget
    options:
      members: true
      inherited_members: false
      filters: ["!^_"]

::: napari_plot._scatter_widget.ScatterPlotWidget
    options:
      members: true
      inherited_members: false
      filters: ["!^_"]

::: napari_plot._profile_widget.LineProfileWidget
    options:
      members: true
      inherited_members: false
      filters: ["!^_"]

::: napari_plot._profile_widget.CursorProfileWidget
    options:
      members: true
      inherited_members: false
      filters: ["!^_"]

::: napari_plot._histogram_widget.HistogramWidget
    options:
      members: true
      inherited_members: false
      filters: ["!^_"]

::: napari_plot._features_widget.FeaturesPlotWidget
    options:
      members: true
      inherited_members: false
      filters: ["!^_"]

## Plot layers

::: napari_plot.layers
    options:
      members:
        - Areas
        - Band
        - Bar
        - Centroids
        - ErrorBar
        - Image
        - InfLine
        - Line
        - MultiLine
        - Points
        - Rectangles
        - Region
        - Scatter
        - Shapes
        - Text
        - Vectors

## Statistical plots

::: napari_plot.stats.categorical.barplot

::: napari_plot.stats.categorical.boxenplot

::: napari_plot.stats.categorical.boxplot

::: napari_plot.stats.facets.catplot

::: napari_plot.stats.matrix.clustermap

::: napari_plot.stats.categorical.countplot

::: napari_plot.stats.facets.displot

::: napari_plot.stats.distributions.distplot

::: napari_plot.stats.distributions.ecdfplot

::: napari_plot.stats.matrix.heatmap

::: napari_plot.stats.distributions.histplot

::: napari_plot.stats.facets.jointplot

::: napari_plot.stats.distributions.kdeplot

::: napari_plot.stats.relational.lineplot

::: napari_plot.stats.facets.lmplot

::: napari_plot.stats.facets.pairplot

::: napari_plot.stats.categorical.pointplot

::: napari_plot.stats.relational.regplot

::: napari_plot.stats.relational.relplot

::: napari_plot.stats.distributions.rugplot

::: napari_plot.stats.relational.scatterplot

::: napari_plot.stats.categorical.stripplot

::: napari_plot.stats.categorical.swarmplot

::: napari_plot.stats.categorical.violinplot
