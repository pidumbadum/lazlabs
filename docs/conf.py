import os
import sys

# Добавляем путь к проекту для автогенерации API
sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('../packages/core'))

#информация о проекте
project = 'Lazlabs School'
copyright = '2026, Kukarachi'
author = 'Kukarachi duo'
release = '1.0.0'

#общие настройки
extensions = [
    'sphinx.ext.autodoc',      # Автогенерация документации из docstrings
    'sphinx.ext.viewcode',     # Добавление ссылок на исходный код
    'sphinx.ext.napoleon',     # Поддержка Google-style docstrings
    'sphinx.ext.intersphinx',  # Ссылки на внешнюю документацию
]

# Настройки autodoc
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'private-members': False,
    'special-members': '__init__',
    'show-inheritance': True,
}

# Настройки Napoleon (Google-style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True

# Настройки intersphinx
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'flask': ('https://flask.palletsprojects.com/en/3.0.x/', None),
}

#Templates путь
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

#настройки для HTML
html_theme = 'sphinx_rtd_theme'  # Тема Read the Docs
html_static_path = ['../static']
html_logo = None
html_favicon = None 

# Настройки темы
html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'style_external_links': True,
}

#Настройки LaTeX
latex_elements = {
    'preamble': r'''
    \usepackage{utf8}
    \usepackage[russian]{babel}
    ''',
}