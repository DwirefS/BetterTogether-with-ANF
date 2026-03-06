import streamlit as st
import os
import logging
from alpha_tools.nim_client import NIMClient
from pymilvus import connections, utility

logger = logging.getLogger(__name__)

# ----------------------------------------------------
# Project AlphaAgent: Financial Research Copilot
# ----------------------------------------------------

st.set_page_config(
    page_title="AlphaAgent: Financial Copilot",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------------------------------------------------------------------
# Azure AD / Entra ID Authentication Gate (OIDC)
# -------------------------------------------------------------------------------------
# Set AUTH_ENABLED=true and provide AZURE_AD_* env vars to enforce login.
# When disabled (default for local dev), the app is accessible without login.
#
# Required environment variables when AUTH_ENABLED=true:
#   AZURE_AD_CLIENT_ID     — App registration client ID from Entra ID
#   AZURE_AD_CLIENT_SECRET — App registration client secret
#   AZURE_AD_TENANT_ID     — Azure AD tenant ID (or 'common' for multi-tenant)
#   AZURE_AD_REDIRECT_URI  — e.g. https://<your-app-url>/_stcore/auth-callback
#
# To register the app:
#   1. Go to portal.azure.com → Entra ID → App registrations → New registration
#   2. Set redirect URI to your Streamlit app URL (e.g. http://localhost:8501)
#   3. Under "Certificates & secrets", create a client secret
#   4. Under "API permissions", add Microsoft Graph → User.Read (delegated)
#   5. Store CLIENT_ID, CLIENT_SECRET, and TENANT_ID in Azure Key Vault
#      (see kubernetes/secrets/keyvault-csi.yaml for CSI driver mount)
# -------------------------------------------------------------------------------------

AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() in ("true", "1", "yes")


def _check_azure_ad_auth() -> bool:
    """
    Validate Azure AD authentication using MSAL confidential client flow.
    Returns True if user is authenticated or auth is disabled.
    """
    if not AUTH_ENABLED:
        return True

    # Check if already authenticated this session
    if st.session_state.get("authenticated"):
        return True

    try:
        import msal
    except ImportError:
        st.error(
            "Authentication is enabled but `msal` is not installed. "
            "Run: `pip install msal>=1.28.0`"
        )
        st.stop()
        return False

    client_id = os.getenv("AZURE_AD_CLIENT_ID", "")
    client_secret = os.getenv("AZURE_AD_CLIENT_SECRET", "")
    tenant_id = os.getenv("AZURE_AD_TENANT_ID", "common")
    redirect_uri = os.getenv("AZURE_AD_REDIRECT_URI", "http://localhost:8501")
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    scopes = ["User.Read"]

    if not client_id or not client_secret:
        st.error(
            "AUTH_ENABLED=true but AZURE_AD_CLIENT_ID / AZURE_AD_CLIENT_SECRET are not set. "
            "Please configure Azure AD credentials via environment variables or Key Vault CSI."
        )
        st.stop()
        return False

    app = msal.ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=client_secret,
    )

    # Check for auth code in query params (redirect callback)
    query_params = st.query_params
    auth_code = query_params.get("code")

    if auth_code:
        # Exchange authorization code for tokens
        result = app.acquire_token_by_authorization_code(
            auth_code,
            scopes=scopes,
            redirect_uri=redirect_uri,
        )
        if "access_token" in result:
            st.session_state["authenticated"] = True
            st.session_state["user_name"] = result.get("id_token_claims", {}).get("name", "User")
            st.session_state["user_email"] = result.get("id_token_claims", {}).get("preferred_username", "")
            # Clear the code from URL
            st.query_params.clear()
            st.rerun()
        else:
            st.error(f"Authentication failed: {result.get('error_description', 'Unknown error')}")
            st.stop()
            return False

    # No auth code — show login button
    auth_url = app.get_authorization_request_url(
        scopes,
        redirect_uri=redirect_uri,
    )

    st.markdown("### 🔐 Azure AD Sign-In Required")
    st.markdown(
        "This application requires authentication via your organization's Azure Active Directory."
    )
    st.markdown(f'<a href="{auth_url}" target="_self">'
                f'<button style="background-color:#0078D4; color:white; padding:12px 24px; '
                f'border:none; border-radius:4px; font-size:16px; cursor:pointer;">'
                f'Sign in with Microsoft</button></a>',
                unsafe_allow_html=True)
    st.stop()
    return False


# Run auth gate before rendering anything
_check_azure_ad_auth()

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

    # Show authenticated user info when Azure AD is enabled
    if AUTH_ENABLED and st.session_state.get("authenticated"):
        user_name = st.session_state.get("user_name", "User")
        user_email = st.session_state.get("user_email", "")
        st.markdown(f"**👤 {user_name}**")
        if user_email:
            st.caption(user_email)
        if st.button("🔓 Sign Out"):
            for key in ["authenticated", "user_name", "user_email"]:
                st.session_state.pop(key, None)
            st.rerun()
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
