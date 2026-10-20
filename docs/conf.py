import os, sys
sys.path.insert(0, os.path.abspath(".."))

project = "mini-Zemax"
author = "Physics Software Project"
release = "0.2.0"

extensions = [
    "sphinx.ext.autodoc",       # справочник из docstrings
    "sphinx.ext.viewcode",      # кнопка [source] у каждого символа
    "sphinx.ext.napoleon",      # google/numpy docstrings
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",       # интерактивная математика
    "sphinxcontrib.mermaid",    # диаграммы связей текстом
]

# GUI-зависимости не нужны для сборки справочника
autodoc_mock_imports = ["PyQt5", "PyQt6", "PySide6", "OpenGL", "pyqtgraph"]
autodoc_member_order = "bysource"

try:
    import sphinx_rtd_theme  # noqa: F401
    html_theme = "sphinx_rtd_theme"
except ImportError:
    html_theme = "alabaster"

intersphinx_mapping = {"python": ("https://docs.python.org/3", None),
                       "numpy": ("https://numpy.org/doc/stable", None)}
mathjax3_config = {"tex": {"tags": "ams"}}
