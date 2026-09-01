"""Shared Streamlit chrome for the multipage app.

Small, page-agnostic UI pieces that every page in ``app_pages/`` renders.
Page *bodies* stay in ``fiscal_model/ui/``; this package holds only the frame.
"""

from .chrome import render_chrome, render_page_footer

__all__ = ["render_chrome", "render_page_footer"]
