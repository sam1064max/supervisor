"""Supervisor - Multi-Agent Supervisor Demo Dashboard.

Run with: streamlit run frontend/app.py   (from the Supervisor repo root)
Uses the offline fake provider by default; set SUPERVISOR_LLM_PROVIDER + API keys for real LLMs.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import time

import streamlit as st

st.set_page_config(
    page_title="Supervisor",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Supervisor")
st.caption("Multi-agent supervisor with routing, guardrails, and recovery (offline demo via fake provider)")

EXAMPLE_QUERIES = [
    "What is 17 x 32?",
    "Compute 100 / 4",
    "Research solar vs wind power.",
    "Explain transformer attention.",
    "What is 2 to the power of 10?",
]


@st.cache_resource
def get_supervisor():
    from supervisor import Supervisor

    return Supervisor()


def render_state(state: dict):
    if not state:
        return
    selected = state.get("selected_agents") or state.get("agent_selection") or []
    if selected:
        st.subheader("Selected Agents")
        st.write(selected)

    order = state.get("execution_order")
    if order:
        st.subheader("Execution Order")
        st.write(order)

    step = state.get("step") or state.get("current_step")
    if step:
        st.subheader("Step")
        st.write(step)


def main():
    with st.sidebar:
        st.header("Controls")
        example = st.selectbox("Example query", [""] + EXAMPLE_QUERIES)
        query = st.text_area("Query", value=example or "What is 17 x 32?", height=100)
        run = st.button("Run", type="primary", use_container_width=True)

    if not run:
        st.info("Enter a query and press **Run** to execute the supervisor graph.")
        return

    if not query.strip():
        st.warning("Please enter a query.")
        return

    try:
        sv = get_supervisor()
        with st.spinner("Running supervisor graph..."):
            start = time.monotonic()
            result = sv.run(query.strip())
            elapsed = time.monotonic() - start

        st.caption(f"Completed in {elapsed:.2f}s")

        if result.error:
            st.error(str(result.error))
        if result.rejection_reason:
            st.warning(f"Guardrail rejection: {result.rejection_reason}")

        if result.final_answer:
            st.subheader("Final Answer")
            st.success(result.final_answer)

        render_state(result.state)

        with st.expander("Raw result"):
            st.json(
                {
                    "final_answer": result.final_answer,
                    "state": result.state,
                    "trace_id": result.trace_id,
                    "request_id": result.request_id,
                    "duration_ms": result.duration_ms,
                    "error": result.error,
                    "rejection_reason": result.rejection_reason,
                    "awaiting_human": result.awaiting_human,
                },
                default=str,
            )
    except Exception as exc:  # noqa: BLE001
        st.error(f"Execution failed: {exc}")


main()
