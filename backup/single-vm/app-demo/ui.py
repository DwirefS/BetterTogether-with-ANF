"""
AlphaAgent — Streamlit Frontend
Capital Markets Agentic Research Copilot UI.

Features:
  - Chat-style query interface with curated demo buttons
  - Agent chain-of-thought trace viewer
  - Retrieved evidence expander
  - ANF data browser sidebar
  - Better Together branding
"""

from __future__ import annotations

import time
from pathlib import Path

import streamlit as st

from .config import get_settings
from .indexer import load_index
from .agent import run_query, AgentResult
from .skills.anf_reader import list_anf_files


# ── Page Config ──
st.set_page_config(
    page_title="AlphaAgent — Capital Markets Copilot",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ──
st.markdown("""
<style>
    .stApp { font-family: 'Inter', 'Segoe UI', sans-serif; }
    .main-title {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #e2e8f0;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        border-left: 4px solid #76b900;
    }
    .main-title h1 { color: #f8fafc; margin: 0; font-size: 1.8rem; }
    .main-title p { color: #94a3b8; margin: 0.3rem 0 0; font-size: 0.95rem; }
    .pillar-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 0.8rem 1rem;
        border-radius: 8px;
        margin: 0.3rem 0;
        border-left: 3px solid #76b900;
    }
    .pillar-card strong { color: #e2e8f0; }
    .pillar-card span { color: #94a3b8; font-size: 0.85rem; }
    .trace-step {
        background: #f1f5f9;
        padding: 0.6rem 1rem;
        border-radius: 8px;
        margin: 0.3rem 0;
        border-left: 3px solid #3b82f6;
        font-size: 0.9rem;
    }
    .compliance-pass { border-left-color: #22c55e !important; }
    .compliance-flag { border-left-color: #ef4444 !important; }
</style>
""", unsafe_allow_html=True)

# ── Load Settings ──
s = get_settings()

# ── Header ──
st.markdown("""
<div class="main-title">
    <h1>🏦 AlphaAgent — Capital Markets Research Copilot</h1>
    <p>Azure Cloud + NVIDIA NIM on Azure + Azure NetApp Files — Better Together</p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ──
with st.sidebar:
    st.markdown("### 🏗️ Architecture")
    st.markdown("""
    <div class="pillar-card">
        <strong>☁️ Azure Cloud</strong><br/>
        <span>GPU VM (N-series) · VNet isolation · NSG</span>
    </div>
    <div class="pillar-card">
        <strong>🧠 NVIDIA on Azure</strong><br/>
        <span>Nemotron LLM · EmbedQA NIM · GPU inference</span>
    </div>
    <div class="pillar-card">
        <strong>💾 Azure NetApp Files</strong><br/>
        <span>NFS mount · Object REST API · Sub-ms latency</span>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.markdown("### 📂 ANF Data Browser")
    anf_files = list_anf_files(s.data_root)
    if anf_files:
        for f in anf_files:
            st.markdown(f"📄 `{f['category']}/{f['name']}` ({f['size_kb']} KB)")
    else:
        st.info("No files found on ANF mount. Data will be generated on first run.")

    st.divider()
    st.markdown("### ⚙️ Runtime Config")
    st.code(
        f"LLM: {s.llm_model}\n"
        f"Embed: {s.embed_model}\n"
        f"Data: {s.data_root}\n"
        f"Index: {s.index_root}\n"
        f"Top-K: {s.top_k}",
        language="text",
    )

    anf_endpoint = s.anf_object_endpoint
    if anf_endpoint:
        st.success(f"Object REST API: {anf_endpoint}")
    else:
        st.info("Object REST API: Not configured (using NFS direct)")


# ── Load Index ──
@st.cache_resource(show_spinner=False)
def _load_index():
    return load_index(s.index_root)


try:
    records, matrix = _load_index()
    index_ready = True
except FileNotFoundError:
    index_ready = False
    st.warning(
        "⏳ Index not ready yet. If you just deployed, the init container is building it. "
        "Refresh in a minute."
    )

# ── Main Content ──
col_left, col_right = st.columns([2, 1])

with col_right:
    st.markdown("### 🎯 Demo Scenarios")
    st.markdown("Click a button to auto-fill a curated query:")

    demo_queries = {
        "📊 Investment Memo": "Create an investment memo for ALPH focusing on catalysts, key risks, and capital expenditure analysis.",
        "🔍 RAG Research": "What are the key risk factors for BETA according to their latest filing?",
        "📈 Comparative": "Compare the EBITDA margins, leverage ratios, and CapEx trends across ALPH, BETA, and GAMM.",
        "✅ Compliance": "Review GAMM's financial metrics against our internal trade surveillance policy thresholds.",
        "🧮 Financial Math": "Calculate the year-over-year CapEx variance for ALPH and check if it triggers any policy alerts.",
    }

    selected_query = None
    for label, query in demo_queries.items():
        if st.button(label, use_container_width=True):
            selected_query = query

with col_left:
    st.markdown("### 💬 Ask the Research Copilot")

    default_value = selected_query or ""
    question = st.text_area(
        "Enter your financial research question:",
        value=default_value,
        height=100,
        placeholder="e.g., Create an investment memo for ALPH focusing on catalysts and risks...",
    )

    run_btn = st.button("🚀 Run Agent", type="primary", disabled=not index_ready)

# ── Agent Execution ──
if run_btn and question and index_ready:
    st.divider()

    with st.spinner("🧠 AlphaAgent is thinking..."):
        result = run_query(
            question=question,
            settings=s,
            records=records,
            matrix=matrix,
        )

    # ── Agent Trace (Chain of Thought) ──
    st.markdown("### 🔗 Agent Chain of Thought")
    for step in result.trace:
        emoji = step.agent.split(" ")[0] if step.agent else "🔹"
        st.markdown(
            f'<div class="trace-step">'
            f"<strong>{step.agent}</strong> → {step.action} "
            f"<span style='color:#64748b'>({step.duration_ms}ms)</span><br/>"
            f"<span style='color:#475569; font-size:0.85rem'>{step.output_summary}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    st.caption(f"⏱️ Total processing time: {result.total_ms}ms")

    # ── Main Answer ──
    st.markdown("### 📝 Response")
    st.markdown(result.answer)

    # ── Math Results ──
    if result.math_results:
        with st.expander(f"🧮 Calculation Details ({len(result.math_results)} calculations)", expanded=False):
            for mr in result.math_results:
                st.markdown(f"**{mr.get('ticker', '')} — {mr.get('calculation', '')}**")
                st.markdown(f"- Formula: `{mr.get('formula', '')}`")
                st.markdown(f"- Inputs: {mr.get('inputs', '')}")
                st.markdown(f"- **Result: {mr.get('result', '')}**")
                if "interpretation" in mr:
                    st.markdown(f"- {mr['interpretation']}")
                st.divider()

    # ── Compliance Assessment ──
    if result.compliance:
        status = result.compliance["overall_status"]
        css_class = "compliance-pass" if status == "PASS" else "compliance-flag"
        with st.expander(f"✅ Compliance Assessment — {status}", expanded=status == "FLAG"):
            st.markdown(
                f'<div class="trace-step {css_class}">'
                f"<strong>Overall: {status}</strong> — "
                f"{result.compliance['passes']} passed, {result.compliance['flags']} flagged"
                f"</div>",
                unsafe_allow_html=True,
            )
            for finding in result.compliance.get("findings", []):
                icon = "🚩" if finding["status"] == "FLAG" else "✅"
                st.markdown(f"{icon} **{finding['metric']}**: {finding['value']} (threshold: {finding['threshold']})")
                st.markdown(f"  ↳ {finding['detail']}")
            st.markdown(f"\n**{result.compliance['recommendation']}**")

    # ── Retrieved Evidence ──
    if result.citations:
        with st.expander(f"📚 Retrieved Evidence ({len(result.citations)} chunks)", expanded=False):
            for h in result.citations:
                st.markdown(f"**{h['doc_id']}** (similarity: {h['score']:.3f})")
                st.text(h["text"][:300] + ("..." if len(h["text"]) > 300 else ""))
                st.divider()

# ── Footer ──
st.divider()
st.markdown(
    "<div style='text-align:center; color:#64748b; font-size:0.8rem'>"
    "AlphaAgent — Azure + NVIDIA + Azure NetApp Files | "
    "All data is synthetic | Built for NVIDIA GTC"
    "</div>",
    unsafe_allow_html=True,
)
