#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Configuration file for the Sphinx documentation builder.

# -- Path setup --------------------------------------------------------------

import datetime
import importlib.metadata
import os
import sys
sys.path.insert(0, os.path.abspath('../src'))

# Verify the source path exists
if not os.path.exists(os.path.abspath('../src')):
    import warnings
    warnings.warn("Source directory '../src' not found. API documentation may be incomplete.")

# -- Project information -----------------------------------------------------

project = 'rms-vicar'
copyright = f'{datetime.date.today().year}, SETI Institute'
author = 'SETI Institute'

# The full version, including alpha/beta/rc tags
try:
    release = importlib.metadata.version('rms-vicar')
except importlib.metadata.PackageNotFoundError:
    release = '1.0.0'  # fallback for development

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'myst_parser',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The suffix(es) of source filenames.
source_suffix = ['.rst', '.md']

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ['_static']

add_module_names = False

# -- Extension configuration -------------------------------------------------

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = True
napoleon_use_param = True
napoleon_use_rtype = True
# Preprocessing lets the aliases below turn the short names the docstrings use into
# references that intersphinx can resolve.
napoleon_preprocess_types = True
napoleon_type_aliases = {
    'np.ndarray': 'numpy.ndarray',
    'Path': 'pathlib.Path',
    'FCPath': 'filecache.file_cache_path.FCPath',
    'file': 'io.IOBase',
    'iterator': 'collections.abc.Iterator',
}
napoleon_attr_annotations = True

# Intersphinx settings
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'filecache': ('https://rms-filecache.readthedocs.io/en/latest/', None),
}

# Nitpicky mode: report every cross-reference that does not resolve. Set here rather
# than passed as -n so that every build gets it -- the check script, CI, and
# scripts/read-docs.sh alike -- and none of them can drift out of step.
nitpicky = True

# The only cross-references that cannot resolve are the informal type words this
# project's docstrings use to describe what an argument accepts. They name no Python
# object, so there is nothing for Sphinx to link them to. Anything that does name a real
# object is expected to resolve, so do not add entries here for symbols we own or for
# third-party classes with an intersphinx inventory; fix the reference instead.
nitpick_ignore_regex = [
    # Napoleon splits a type such as "(bool, optional)" on the comma and looks up each
    # piece, so the trailing "optional" of every optional parameter arrives here.
    (r'py:class', r'optional'),
    (r'py:class', r'string'),
    (r'py:class', r'name'),
    (r'py:class', r'array-like'),
]

# MyST-Parser settings
myst_enable_extensions = [
    "colon_fence",
    "deflist",
]
