"""
Fiscal Policy Impact Calculator - Main Streamlit App.

URL routing:
  /              — Main calculator
  /?mode=classroom&assignment=laffer_curve  — Classroom mode
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from fiscal_model.ui.runtime_logging import (
    build_runtime_metadata,
    configure_runtime_logger,
    log_runtime_event,
)


def _render_head_metadata(st_module) -> None:
    st_module.set_page_config(
        page_title="Fiscal Policy Impact Calculator — CBO-Validated Budget Scoring",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st_module.markdown(
        """
        <meta name="description" content="Estimate the budgetary impact of tax and spending proposals. 25+ policies validated within 15% of CBO/JCT scores.">
        <meta property="og:title" content="Fiscal Policy Impact Calculator — CBO-Validated Budget Scoring">
        <meta property="og:description" content="Estimate the budgetary impact of tax and spending proposals. 25+ policies validated within 15% of CBO/JCT scores.">
        <meta property="og:type" content="website">
        <meta name="twitter:card" content="summary">
        <meta name="twitter:title" content="Fiscal Policy Impact Calculator — CBO-Validated Budget Scoring">
        <meta name="twitter:description" content="Estimate the budgetary impact of tax and spending proposals. 25+ policies validated within 15% of CBO/JCT scores.">
        """,
        unsafe_allow_html=True,
    )


def _default_deps_builder(*, pd_module):
    from fiscal_model.ui.dependencies import build_app_dependencies

    return build_app_dependencies(pd_module=pd_module)


def _default_classroom_renderer() -> None:
    from classroom_app import main as classroom_main

    classroom_main()


def main(
    *,
    st_module=st,
    pd_module=pd,
    app_root: Path | None = None,
    deps_builder=None,
    classroom_renderer=None,
) -> None:
    """Bootstrap the main Streamlit app in a testable, import-safe wrapper."""
    logger = configure_runtime_logger(__name__)
    route_mode = getattr(st_module, "query_params", {}).get("mode", "")
    metadata = build_runtime_metadata(entrypoint="app.py", mode=route_mode or "calculator")
    log_runtime_event(logger, "app_boot", **metadata)

    if route_mode == "classroom":
        renderer = classroom_renderer or _default_classroom_renderer
        try:
            log_runtime_event(logger, "app_route", route="classroom")
            renderer()
        except Exception:
            logger.exception("Classroom mode bootstrap failed")
            st_module.error(
                "⚠️ Classroom mode failed to start. Please reload the page or check the deployment logs."
            )
        return

    _render_head_metadata(st_module)

    builder = deps_builder or _default_deps_builder
    app_root = app_root or Path(__file__).parent

    try:
        deps = builder(pd_module=pd_module)
    except ImportError as exc:
        logger.exception("App dependency import failed")
        st_module.error(f"⚠️ Could not import fiscal model: {exc}")
        return

    try:
        deps.apply_app_styles(st_module)
        deps.run_main_app(
            st_module=st_module,
            deps=deps,
            model_available=True,
            app_root=app_root,
        )
    except Exception:
        logger.exception("Main calculator bootstrap failed")
        st_module.error(
            "⚠️ The calculator failed to start. Please reload the page or check the deployment logs."
        )


if __name__ == "__main__":
    main()
