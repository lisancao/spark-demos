"""
Genre Templates — World generation blueprints for different settings.

Each genre module exports a TEMPLATE dict that drives the world generator.
"""

GENRES = {}


def _load_genres():
    """Load all genre templates. Missing modules are silently skipped."""
    import importlib
    modules = [
        ("dark-fantasy", "genre_templates.dark_fantasy"),
        ("modern-crime", "genre_templates.modern_crime"),
        ("high-fantasy", "genre_templates.high_fantasy"),
        ("space-opera", "genre_templates.space_opera"),
        ("post-apocalyptic", "genre_templates.post_apocalyptic"),
    ]
    for genre_id, module_path in modules:
        try:
            mod = importlib.import_module(module_path)
            GENRES[genre_id] = mod.TEMPLATE
        except (ImportError, AttributeError):
            pass


_load_genres()
