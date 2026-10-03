"""
Public-finance "Ask" assistant.

Exposes :class:`FiscalAssistant` for use by the Streamlit Ask tab.
"""

from .assistant import AssistantUpstreamError, FiscalAssistant
from .sources import SOURCES, allowlisted_domain

__all__ = ["SOURCES", "AssistantUpstreamError", "FiscalAssistant", "allowlisted_domain"]
