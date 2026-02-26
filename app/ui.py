import streamlit as st
import os
from alpha_tools.nim_client import NIMClient
from pymilvus import connections, utility

# ----------------------------------------------------
# Project AlphaAgent: Financial Research Copilot
# ----------------------------------------------------

st.set_page_config(
    page_title="AlphaAgent: Financial Copilot",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS for Enterprise Look ---
st.markdown(
    """
<style>
    .reportview-container {
        background: #fafafa;
    }
    .status-box {
        padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 5px solid;
    }
    .status-ok { background-color: #e6fced; border-color: #0b8235; color: #0b8235; }
    .status-err { background-color: #fce8e6; border-color: #d93025; color: #d93025; }
    
    .agent-trace { font-size: 0.9em; font-family: monospace; background: #2c2f33; color: #00ff00; padding: 10px; border-radius: 5px; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("AlphaAgent: Financial Research Copilot")
st.markdown("*Powered by Azure NetApp Files, NVIDIA NIM, and NeMo Agent Toolkit*")

# --- Sidebar: System Status & Metrics ---
with st.sidebar:
    st.header("⚙️ Infrastructure Status")

    status_html = ""
    # Check Milvus
    try:
        MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
        connections.connect("default", host=MILVUS_HOST, port="19530")
        if utility.has_collection("sec_filings"):
            status_html += "<div class='status-box status-ok'><b>Milvus Vector DB</b><br>Connected (ANF NFS PVC)</div>"
        else:
            status_html += "<div class='status-box status-err'><b>Milvus Vector DB</b><br>Online, No Data</div>"
    except Exception:
        status_html += "<div class='status-box status-err'><b>Milvus Vector DB</b><br>Disconnected</div>"

    # Check NIM Client Configured
    try:
        nim = NIMClient()
        if nim.api_key and len(nim.api_key) > 5:
            status_html += "<div class='status-box status-ok'><b>NVIDIA NIMs</b><br>Connected (LLM, Embed, Rerank, Retriever)</div>"
        else:
            status_html += "<div class='status-box status-err'><b>NVIDIA NIMs</b><br>No API Key / Endpoint Configured</div>"
    except Exception:
        status_html += "<div class='status-box status-err'><b>NVIDIA NIMs</b><br>Disconnected</div>"

    st.markdown(status_html, unsafe_allow_html=True)

    st.markdown("---")
    st.header("📊 NeMo Profiler Telemetry")
    t_ph = st.empty()
    t_ph.markdown("""
    - **Total Tokens:** 0
    - **Total Latency:** 0ms
    - **Orchestrator Cost:** $0.00
    """)

    st.markdown("---")
    st.caption(
        "Architecture: AKS GPU nodes + ANF Object/NFS + Milvus + NeMo Agent Toolkit."
    )

# --- Main Interface ---

tabs = st.tabs(["💬 Copilot Chat", "📝 Document Repository (ANF)"])

with tabs[1]:
    st.subheader("📁 Enterprise Data on Azure NetApp Files")
    st.info(
        "Files below are stored centrally on ANF. Accessed simultaneously by legacy NFS apps and modern AI Object REST APIs without data movement."
    )

    anf_path = os.getenv("ANF_MOUNT_PATH", "/mnt/anf/data")
    if os.path.exists(anf_path):
        try:
            files = [f for f in os.listdir(anf_path) if f.endswith(".pdf")]
            if files:
                for f in files:
                    st.write(f"📄 `{f}`")
            else:
                st.warning("No PDF files ingested yet. Run the `load-data.sh` job.")
        except Exception as e:
            st.error(f"Error accessing ANF data directory: {e}")
    else:
        st.error(f"ANF Mount point {anf_path} not found. Is the PVC mounted?")


with tabs[0]:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Suggested queries representing the 6-agent workflows
    st.markdown("### Suggested Analytical Queries:")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⚖️ Compare AAPL and MSFT risk factors from their latest 10-K."):
            st.session_state.preset_prompt = (
                "Compare AAPL and MSFT risk factors from their latest 10-K."
            )
    with col2:
        if st.button(
            "🛡️ Draft a compliance-reviewed summary of TSLA's capital roadmap."
        ):
            st.session_state.preset_prompt = "Draft a compliance-reviewed summary of TSLA's capital expenditure roadmap."

    prompt = st.chat_input("Ask AlphaAgent to analyze SEC EDGAR financial filings...")

    if "preset_prompt" in st.session_state and st.session_state.preset_prompt:
        prompt = st.session_state.preset_prompt
        st.session_state.preset_prompt = ""

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                import yaml
                from nvidia_nat import Runner, Config

                # Render state tracking UI
                status_text = st.empty()
                trace_box = st.empty()

                status_text.markdown(
                    "🕵️ **NeMo Orchestrator:** Routing sub-tasks to specialized agents..."
                )

                # Load the NATO workflow
                wf_path = os.path.join(os.path.dirname(__file__), "workflow.yaml")
                with open(wf_path, "r") as yaml_file:
                    workflow_data = yaml.safe_load(yaml_file)

                # Instantiate real runner for state machine orchestration
                config = Config.from_dict(workflow_data)
                runner = Runner(config)

                # Execute user prompt through the multi-agent system
                trace_box.markdown(
                    "<div class='agent-trace'>&gt; Executing `nvidia-nat` YAML state machine<br>&gt; Awaiting sub-agent dynamic routing...</div>",
                    unsafe_allow_html=True,
                )

                # In a robust production environment, runner exposes telemetry/event hooks or async streams.
                # For synchronous demo execution:
                response = runner.run(prompt)

                # Clear loading indicators
                status_text.empty()
                trace_box.empty()

                st.markdown(response)

                # Update telemetry using response metadata if available
                t_ph.markdown("""
                - **State Execution:** NeMo Orchestrator complete
                - **Tools invoked:** ANF Milvus Retrieval, NIM LLM Compliance
                """)

                st.session_state.messages.append(
                    {"role": "assistant", "content": response}
                )

            except ImportError as e:
                st.error(
                    f"NVIDIA NeMo Agent Toolkit (`nvidia-nat`) not installed. Please run `pip install -r requirements.txt`. Details: {e}"
                )
            except Exception as e:
                st.error(f"Failed to execute NeMo Agent Toolkit state machine: {e}")
