# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))
import napari_plot

release = napari_plot.__version__
if "dev" in release:
    version = "dev"
else:
    version = release

# -- Project information -----------------------------------------------------

project = "napari-plot"
copyright = "2022, The napari-plot team"
author = "The napari-plot team"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
autosummary_generate = True
autosummary_imported_members = True
comments_config = {"hypothesis": False, "utterances": False}

# execution_allow_errors = False
# execution_excludepatterns = []
# execution_in_temp = False
# execution_timeout = 30

extensions = [
    "sphinx.ext.napoleon",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx_external_toc",
    "sphinx_tabs.tabs",
    "myst_nb",
    #    "sphinx_comments",
    "sphinx_panels",
    "sphinx.ext.viewcode",
]

external_toc_path = "_toc.yml"
external_toc_exclude_missing = True


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

jupyter_cache = ""
jupyter_execute_notebooks = "auto"

myst_enable_extensions = [
    "colon_fence",
    "dollarmath",
    "substitution",
    "tasklist",
]

nb_output_stderr = "show"

panels_add_bootstrap_css = False
pygments_style = "solarized-dark"
suppress_warnings = ["myst.header", "etoc.toctree"]


# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    ".jupyter_cache",
    "jupyter_execute",
]
