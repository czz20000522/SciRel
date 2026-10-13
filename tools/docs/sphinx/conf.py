project = 'SciRel'
author = 'SciRel'
copyright = '2026, SciRel'
language = 'zh_CN'
extensions = ['sphinx_copybutton', 'sphinx_design']
html_theme = 'pydata_sphinx_theme'
html_title = 'SciRel 中文文档'
html_static_path = ['_static']
html_css_files = ['scirel.css']
html_js_files = ['scirel.js']
html_copy_source = False
html_show_sourcelink = False
html_domain_indices = False
html_use_index = False
html_search_language = 'zh'
html_sidebars = {'index': ['search-button-field'], '**': ['search-button-field', 'sidebar-nav-bs']}
html_theme_options = {
    'logo': {'text': 'SciRel'},
    'navbar_start': ['navbar-logo'],
    'navbar_end': [],
    'navbar_persistent': [],
    'header_links_before_dropdown': 5,
    'secondary_sidebar_items': ['page-toc'],
    'navigation_depth': 4,
    'show_nav_level': 1,
    'show_prev_next': True,
    'footer_start': ['copyright'],
    'footer_end': ['sphinx-version', 'theme-version'],
}
html_context = {'default_mode': 'light'}
copybutton_prompt_text = r'>>> |\.\.\. |\$ '
copybutton_prompt_is_regexp = True
copybutton_only_copy_prompt_lines = False
copybutton_exclude = '.linenos, .gp'
copybutton_copy_empty_lines = True
nitpicky = True
rst_prolog = '.. role:: scirel-math(raw)\n   :format: html\n'
exclude_patterns = []
