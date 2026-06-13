"""
Public-finance "Ask" assistant.

Exposes :class:`FiscalAssistant` for use by the Streamlit Ask tab.
"""

from .assistant import FiscalAssistant
from .sources import SOURCES, allowlisted_domain

__all__ = ["SOURCES", "FiscalAssistant", "allowlisted_domain"]
