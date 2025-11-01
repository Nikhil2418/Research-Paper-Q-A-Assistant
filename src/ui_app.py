# Ensure imports work when Streamlit runs from /src
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from src.ingest import build_index
from src.rag_chain import answer_query
from src.utils.pdf_exporter import export_answer_to_pdf

# -------------------------------
# Basic page setup & simple CSS
# -------------------------------
st.set_page_config(page_title="Research Paper Q&A Assistant", page_icon="🧠", layout="wide")

CHAT_CSS = """
<style>
/* tighten top padding */
.block-container { padding-top: 1.2rem; }
/* subtle separators */
hr { border: 0; height: 1px; background: #2c2c2c33; }
/* nicer sidebar headers */
section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {
  margin-bottom: .25rem;
}
/* shrink chat bubbles a bit */
[data-testid="stChatMessage"] { padding: .6rem .8rem; }
</style>
"""
st.markdown(CHAT_CSS, unsafe_allow_html=True)

# Title header
col_logo, col_title = st.columns([0.08, 0.92])
with col_title:
    st.title("Research Paper Q&A Assistant")
    st.caption("RAG • FAISS • LangChain • OpenAI")

# -----------------------------------
# Sidebar: Upload, Build, Preferences
# -----------------------------------
with st.sidebar:
    st.header("Upload Research Papers")
    st.caption("1) Upload PDFs → 2) Build Index → 3) Ask")
    uploaded_files = st.file_uploader("Drop or browse PDF files", type="pdf", accept_multiple_files=True)
    if uploaded_files:
        os.makedirs("data/pdfs", exist_ok=True)
        for file in uploaded_files:
            with open(f"data/pdfs/{file.name}", "wb") as f:
                f.write(file.getbuffer())
        st.success(f"Uploaded {len(uploaded_files)} file(s).")

    if st.button("🔄 Build / Rebuild Index", use_container_width=True):
        with st.spinner("Indexing PDFs (split → embed → store)…"):
            try:
                build_index()
                st.success("Index built successfully ✅")
            except Exception as e:
                st.error(f"{e}")

    st.divider()
    st.subheader("Answer Settings")
    # Model & length controls (these are read when user sends a message)
    model_choice = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o"], index=0)
    style = st.selectbox("Answer length", ["short", "medium", "long"], index=1)
    top_k = st.slider("Retriever Top-K", min_value=3, max_value=10, value=5)
    st.caption("Higher K gives more context (but uses more tokens).")

    st.divider()
    if st.button("🧹 New Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# -----------------------------------
# Session state for chat history
# -----------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# Render existing conversation
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # show sources if available
        cites = msg.get("citations", [])
        if cites:
            with st.expander("📚 Sources"):
                for c in cites:
                    st.write("•", c)

# -----------------------------------
# Chat input (like ChatGPT)
# -----------------------------------
prompt = st.chat_input("Ask a question about your uploaded papers...")
if prompt:
    # 1) Echo the user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2) Generate assistant reply
    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            answer, citations = answer_query(prompt, k=top_k, style=style, model=model_choice)
            placeholder.markdown(answer)
            if citations:
                with st.expander("📚 Sources"):
                    for c in citations:
                        st.write("•", c)
            # Save to history
            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "citations": citations
            })
        except Exception as e:
            placeholder.error(f"Error: {e}")

# -----------------------------------
# Footer actions: download last answer
# -----------------------------------
st.markdown("---")
last_ai = next((m for m in reversed(st.session_state.messages) if m["role"] == "assistant"), None)
btn_cols = st.columns([0.2, 0.8])
with btn_cols[0]:
    if st.button("📄 Download last answer as PDF", disabled=last_ai is None):
        if last_ai:
            try:
                # Find the last user question to include in PDF
                last_user = next((m for m in reversed(st.session_state.messages) if m["role"] == "user"), {"content": "User Question"})
                pdf_path = export_answer_to_pdf(last_user["content"], last_ai["content"], last_ai.get("citations", []))
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Save PDF",
                        data=f,
                        file_name=os.path.basename(pdf_path),
                        mime="application/pdf",
                        use_container_width=True
                    )
            except Exception as e:
                st.error(f"PDF export failed: {e}")
