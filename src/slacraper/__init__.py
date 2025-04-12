"""
slacraper - Slack message scraper tool
"""

from .core import Slacraper

__all__ = ["Slacraper"]

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"
