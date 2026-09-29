"""a11y-audit: accessibility audit of web pages in headless Chromium."""

__version__ = "1.0.0"

__all__ = ["__version__", "audit_urls", "Options"]


def __getattr__(name):
    if name in ("audit_urls", "Options"):
        from . import engine

        return getattr(engine, name)
    raise AttributeError(name)
