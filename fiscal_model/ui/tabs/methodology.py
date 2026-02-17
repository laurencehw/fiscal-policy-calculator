"""
Methodology tab renderer.
"""

from __future__ import annotations

from typing import Any


def render_methodology_tab(st_module: Any) -> None:
    """
    Render methodology/reference tab content.
    """
    st_module.header("ℹ️ Methodology")
    st_module.markdown(
        """
        ## How This Calculator Works
        [Existing content...]
        """
    )
