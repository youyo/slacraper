"""
slacraper - Slack message scraper tool
"""

from .core import SlackScraper

__all__ = ["SlackScraper"]

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"
