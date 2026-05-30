import streamlit as st
import requests
import uuid
import json
from streamlit_cookies_manager import EncryptedCookieManager
import os

API_URL = os.getenv("API_BASE_URL","http://localhost:8000")


st.set_page_config(
    page_title = "Codebase Assistant",
    page_icon =  "🔍",
    layout = "wide",
    initial_sidebar_state = "expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;600;800&display=swap');
 
/* Base */
html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
}
 

/* Hide default streamlit elements but keep the sidebar toggle! */
#MainMenu, footer { visibility: hidden; }
            
header { background-color: transparent !important; }
.block-container { padding-top: 1.5rem; padding-bottom: 0; }
 
/* Background */
.stApp {
    background-color: #0a0a0f;
    color: #e2e8f0;
}
 
/* Sidebar */
[data-testid="stSidebar"] {
    background: #0f0f1a;
    border-right: 1px solid #1e1e2e;
}
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
 
/* Title */
.main-title {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 1.8rem;
    background: linear-gradient(135deg, #60a5fa, #a78bfa, #34d399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0;
    letter-spacing: -0.5px;
}
 
.sub-title {
    font-size: 0.8rem;
    color: #4a5568;
    font-family: 'JetBrains Mono', monospace;
    margin-top: 0.2rem;
    letter-spacing: 1px;
}
 
/* Chat messages */
.user-msg {
    background: #1a1a2e;
    border: 1px solid #2d2d4e;
    border-radius: 12px 12px 4px 12px;
    padding: 0.9rem 1.1rem;
    margin: 0.5rem 0;
    margin-left: 15%;
    font-size: 0.92rem;
    line-height: 1.6;
    color: #e2e8f0;
}
 
.assistant-msg {
    background: #0f1629;
    border: 1px solid #1e3a5f;
    border-left: 3px solid #60a5fa;
    border-radius: 4px 12px 12px 12px;
    padding: 0.9rem 1.1rem;
    margin: 0.5rem 0;
    margin-right: 10%;
    font-size: 0.92rem;
    line-height: 1.7;
    color: #cbd5e1;
    font-family: 'Syne', sans-serif;
}
 
/* Steps badge */
.steps-container {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-top: 0.7rem;
    padding-top: 0.7rem;
    border-top: 1px solid #1e3a5f;
}
 
.step-badge {
    background: #0d2137;
    border: 1px solid #1e4976;
    color: #60a5fa;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    padding: 0.2rem 0.6rem;
    border-radius: 20px;
    letter-spacing: 0.5px;
}
 
.step-arrow {
    color: #2d4a6e;
    font-size: 0.7rem;
    display: flex;
    align-items: center;
}
 
/* Status pills */
.status-pill {
    display: inline-block;
    padding: 0.2rem 0.7rem;
    border-radius: 20px;
    font-size: 0.72rem;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.5px;
}
 
.status-active {
    background: #052e16;
    border: 1px solid #166534;
    color: #4ade80;
}
 
.status-inactive {
    background: #1a0a0a;
    border: 1px solid #7f1d1d;
    color: #f87171;
}
 
/* Input area */
.stChatInput > div {
    background: #0f0f1a !important;
    border: 1px solid #2d2d4e !important;
    border-radius: 12px !important;
}
 
.stChatInput input {
    color: #e2e8f0 !important;
    font-family: 'Syne', sans-serif !important;
}
 
/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #1d4ed8, #7c3aed);
    color: white;
    border: none;
    border-radius: 8px;
    font-family: 'Syne', sans-serif;
    font-weight: 600;
    font-size: 0.85rem;
    padding: 0.5rem 1.2rem;
    transition: opacity 0.2s;
    width: 100%;
}
.stButton > button:hover { opacity: 0.85; }
 
/* Text input */
.stTextInput > div > div > input {
    background: #0f0f1a !important;
    border: 1px solid #2d2d4e !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.82rem !important;
}
 
/* Divider */
hr { border-color: #1e1e2e; }
 
/* Section label */
.section-label {
    font-size: 0.7rem;
    font-family: 'JetBrains Mono', monospace;
    color: #4a5568;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 0.5rem;
}
 
/* Empty state */
.empty-state {
    text-align: center;
    padding: 4rem 2rem;
    color: #2d3748;
}
.empty-state-icon { font-size: 3rem; margin-bottom: 1rem; }
.empty-state-text {
    font-size: 0.9rem;
    line-height: 1.8;
    color: #374151;
}
</style>
""", unsafe_allow_html=True)

cookies = EncryptedCookieManager(
    prefix="codebase_app",
    password="super-secret-key"  
)

if not cookies.ready():
    st.stop()

if "user_id" not in cookies:
    cookies["user_id"] = str(uuid.uuid4())
    cookies.save()

st.session_state.user_id = cookies["user_id"]

if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "repo_url" not in st.session_state:
    st.session_state.repo_url = ""

if "ingested" not in st.session_state:
    st.session_state.ingested = False

if "session_started" not in st.session_state:
    st.session_state.session_started = False

def api_ingest(repo_url, session_id):
    try:
        r = requests.post(
            f"{API_URL}/ingest",
            json = {"repo_url": repo_url, "session_id": session_id},
            headers = {"x-user-id": st.session_state.user_id},
            timeout = 300
        )
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def api_start_session(repo_url):
    try:
        r = requests.post(
           f"{API_URL}/session/start",
           json = {"repo_url": repo_url},
           headers = {"x-user-id": st.session_state.user_id},
           timeout = 30
        )
        return r.json()
    except Exception as e:
        return {"error":str(e)}

def format_steps(steps):
    if not steps:
        return ""
    
    badges = ""
    for i, step in enumerate(steps):
        badges += f'<span class="step-badge">{step}</span>'
        if i < len(steps) - 1:
            badges += '<span class="step-arrow">→</span>'
    
    return f'<div class="steps-container">{badges}</div>'

# --- SIDEBAR ---
with st.sidebar:
    st.markdown('<p class="main-title">⌗ Codebase</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">ASSISTANT v2.0</p>', unsafe_allow_html=True)
    st.markdown("---")

    st.markdown('<p class="section-label">Session</p>', unsafe_allow_html=True)

    if st.session_state.session_started:
        st.markdown(
            '<span class="status-pill status-active">● Active</span>',
            unsafe_allow_html=True
        )
        st.markdown(
            f'<p style="font-family: JetBrains Mono; font-size: 0.7rem; '
            f'color: #4a5568; margin-top: 0.5rem; word-break: break-all;">'
            f'{st.session_state.session_id[:16]}...</p>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<span class="status-pill status-inactive">● No Session</span>',
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.markdown('<p class="section-label">Repository</p>', unsafe_allow_html=True)
 
    repo_url = st.text_input(
        "GitHub URL",
        placeholder="https://github.com/owner/repo",
        label_visibility="collapsed"
    )

    col1 , col2 = st.columns(2)
    with col1:
        start_btn = st.button("▶ Start", use_container_width=True)
    with col2:
        ingest_btn = st.button("⬇ Ingest", use_container_width=True)

    if start_btn and repo_url:
        with st.spinner("Starting session..."):
            result = api_start_session(repo_url)
            session_id = result.get("session_id")

            if session_id:
                st.session_state.session_id = session_id
                st.session_state.session_started = True
                st.session_state.repo_url = repo_url
                st.session_state.messages = []
                st.success("Session Started")
            else:
                st.error(f"Failed: {result.get('error', 'No session_id returned')}")
            st.rerun()

    if ingest_btn and repo_url:
        if not st.session_state.session_started:
            st.warning("Please click 'Start' to create a session first!")
        else:
            with st.spinner("Ingesting repo..."):
                result = api_ingest(repo_url, st.session_state.session_id)
                if "error" in result:
                    st.error(f"Failed: {result['error']}")
                else:
                    st.success("Ingestion complete!")
                    st.session_state.ingested = True

    st.markdown("---")
    st.markdown('<p class="section-label">Quick Queries</p>', unsafe_allow_html=True)
 
    quick_queries = [
        "What are the imports in tools.py?",
        "What are the last 3 commits?",
        "Are there circular dependencies?",
    ]

    for q in quick_queries:
        if st.button(q, use_container_width=True, key=f"quick_{q}"):
            if st.session_state.session_started:
                st.session_state.pending_query = q
            else:
                st.warning("Start a session first")
    
    st.markdown("---")
    if st.button("🗑 Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.markdown(
        f'<p style="font-family: JetBrains Mono; font-size: 0.65rem; '
        f'color: #2d3748; margin-top: 1rem;">uid: {st.session_state.user_id[:12]}...</p>',
        unsafe_allow_html=True
    )

# --- MAIN CHAT AREA ---
col_h1 , col_h2 = st.columns([3,1])
with col_h1:
    if st.session_state.repo_url:
        st.markdown(
            f'<p style="font-family: JetBrains Mono; font-size: 0.78rem; '
            f'color: #4a90d9; margin-bottom: 0;">📂 {st.session_state.repo_url}</p>',
            unsafe_allow_html=True
            )
    else:
        st.markdown(
            '<p style="font-family: JetBrains Mono; font-size: 0.78rem; '
            'color: #4a5568; margin-bottom: 0;">No repo loaded</p>',
            unsafe_allow_html=True
        )

st.markdown("---")

if not st.session_state.messages and "pending_query" not in st.session_state:
    st.markdown("""
        <div class="empty-state">
        <div class="empty-state-icon">⌗</div>
        <div class="empty-state-text">
            Start a session and Ingest a GitHub repo<br>
            to begin asking questions about the codebase
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f'<div class="user-msg">👤 {msg["content"]}</div>', unsafe_allow_html = True)
        else:
            steps_html = format_steps(msg.get("steps" , []))
            st.markdown(
                f'<div class="assistant-msg">'
                f'<span style="color:#60a5fa; font-size:0.8rem; font-family: JetBrains Mono;">⌗ assistant</span><br><br>'
                f'{msg["content"]}<br>{steps_html}</div>',
                unsafe_allow_html=True
            )

# Handle quick queries or direct input
prompt = st.chat_input("Ask anything about the codebase...")
if "pending_query" in st.session_state and st.session_state.pending_query:
    prompt = st.session_state.pending_query
    st.session_state.pending_query = None

if prompt and st.session_state.session_started:
    # 1. Render User Message Instantly
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.markdown(f'<div class="user-msg">👤 {prompt}</div>', unsafe_allow_html = True)

    # 2. Setup placeholders for streaming
    status_placeholder = st.empty()
    msg_placeholder = st.empty()
    
    full_answer = ""
    current_steps = []

    try:
        # 3. Stream from the new backend architecture
        payload = {"session_id": st.session_state.session_id, "query": prompt, "stream": True}
        headers = {"x-user-id": st.session_state.user_id, "Content-Type": "application/json"}
        
        with requests.post(f"{API_URL}/query/stream", headers=headers, json=payload, stream=True) as response:
            if response.status_code != 200:
                st.error(f"API Error: {response.text}")
            else:
                for line in response.iter_lines():
                    if not line:
                        continue
                    
                    try:
                        chunk = json.loads(line.decode('utf-8'))
                        chunk_type = chunk.get("type")
                        chunk_data = chunk.get("data", {})
                        
                        if chunk_type == "thinking":
                            status_placeholder.markdown('<span class="status-pill status-active">🤔 Thinking...</span>', unsafe_allow_html=True)
                            
                        elif chunk_type == "tool_call":
                            tool_name = chunk_data.get("tool_name", "unknown")
                            current_steps.append(tool_name)
                            status_placeholder.markdown(f'<span class="status-pill status-active">🔧 Running {tool_name}...</span>', unsafe_allow_html=True)


                        elif chunk_type == "tool_result":
                            tool_name = chunk_data.get("tool_name","Tool")

                            status_placeholder.markdown(
                                f'''
                                <div class="assistant-msg"
                                style="border-left:3px solid #10b981;">
                                ✅ {tool_name} completed
                                </div>
                                ''',
                                unsafe_allow_html=True
                            )



                        elif chunk_type == "reasoning":
                            reasoning = chunk_data.get("analysis" , {})

                            status_placeholder.markdown(
                                f'''
                                <div class="assistant-msg"
                                style="border-left:3px solid #f59e0b;">
                                🧠 {reasoning}
                                </div>
                                ''',
                                unsafe_allow_html=True
                            )

                            
                            # Real-time update of the assistant div with the new steps badge!
                            steps_html = format_steps(current_steps)
                            msg_placeholder.markdown(
                                f'<div class="assistant-msg">'
                                f'<span style="color:#60a5fa; font-size:0.8rem; font-family: JetBrains Mono;">⌗ assistant</span><br><br>'
                                f'{full_answer}▌<br>{steps_html}</div>',
                                unsafe_allow_html=True
                            )
                            
                        elif chunk_type == "text":
                            status_placeholder.empty()
                            full_answer += chunk_data.get("text", "")
                            steps_html = format_steps(current_steps)
                            
                            # Stream the text inside your beautiful custom div
                            msg_placeholder.markdown(
                                f'<div class="assistant-msg">'
                                f'<span style="color:#60a5fa; font-size:0.8rem; font-family: JetBrains Mono;">⌗ assistant</span><br><br>'
                                f'{full_answer}▌<br>{steps_html}</div>',
                                unsafe_allow_html=True
                            )
                            
                        elif chunk_type == "end":
                            status_placeholder.empty()
                            steps_html = format_steps(current_steps)
                            
                            # Remove the blinking cursor (▌) at the end
                            msg_placeholder.markdown(
                                f'<div class="assistant-msg">'
                                f'<span style="color:#60a5fa; font-size:0.8rem; font-family: JetBrains Mono;">⌗ assistant</span><br><br>'
                                f'{full_answer}<br>{steps_html}</div>',
                                unsafe_allow_html=True
                            )

                        elif chunk_type == "error":
                            status_placeholder.empty()
                            error_msg = chunk_data.get("error", "Unknown backend error")
                            msg_placeholder.markdown(
                                f'<div class="assistant-msg" style="border-left: 3px solid #f87171;">'
                                f'<span style="color:#f87171; font-weight:600;">❌ Agent Error</span><br><br>'
                                f'{error_msg}</div>', 
                                unsafe_allow_html=True
                            )
                            break
                            
                    except json.JSONDecodeError:
                        pass
        
        # Save to memory so it stays on screen when the page refreshes
        st.session_state.messages.append({
            "role": "assistant", 
            "content": full_answer, 
            "steps": current_steps
        })

    except Exception as e:
        st.error(f"Connection failed: {e}")

elif prompt and not st.session_state.session_started:
    st.warning("Please click 'Start' in the sidebar to begin a session first!") 