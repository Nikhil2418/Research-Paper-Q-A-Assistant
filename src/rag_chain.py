import os, re
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()
INDEX_DIR = "data/index/faiss"

def _index_exists() -> bool:
    return (
        os.path.exists(os.path.join(INDEX_DIR, "index.faiss")) and
        os.path.exists(os.path.join(INDEX_DIR, "index.pkl"))
    )

RAG_PROMPT = ChatPromptTemplate.from_template("""
You are an intelligent research assistant for academic papers.
Write a {style_note} answer using ONLY the provided context.
If the information isn't present, say: "I could not find this in the uploaded papers."

Question:
{question}

Context:
{context}

Use clear structure and include inline source tags like [PaperName.pdf] where relevant.
""")

# --- NEW: small helper to pull Abstract text if present in any chunk
_ABS_STOP = r"(?:\n\s*(?:Keywords|Index\\s*Terms|Index-Terms|1\\.|I\\.|Introduction)\\b)"
_ABS_PAT = re.compile(r"(?is)\\bAbstract\\b\\s*[:—-]?\\s*(.+?)" + _ABS_STOP)

def _try_extract_abstract(text: str) -> str | None:
    m = _ABS_PAT.search(text)
    if m:
        abstract = m.group(1).strip()
        # keep it tidy
        return re.sub(r"\\s{2,}", " ", abstract)[:2200]
    return None

def answer_query(query: str, k: int = 5, style: str = "medium", model: str = "gpt-4o-mini"):
    if not _index_exists():
        return ("⚠️ No FAISS index found. Please upload PDFs and click **Build / Rebuild Index** "
                "in the sidebar."), []

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    db = FAISS.load_local(INDEX_DIR, embeddings, allow_dangerous_deserialization=True)

    # MMR diversifies retrieval → better chance of catching short sections like Abstract
    retriever = db.as_retriever(
        search_type="mmr",
        search_kwargs={"k": k, "fetch_k": max(20, 4 * k)}
    )
    docs = retriever.invoke(query)

    if not docs:
        return "❌ No relevant content found.", []

    # ---- Abstract special-case fallback
    if "abstract" in query.lower():
        # Scan top 12 chunks quickly for an Abstract heading
        extra_docs = retriever.invoke("Abstract section of the paper")
        pool = docs + [d for d in extra_docs if d not in docs]
        for d in pool[:12]:
            found = _try_extract_abstract(d.page_content)
            if found:
                title = d.metadata.get("title", "Unknown")
                ans = f"**Abstract** — [{title}]\n\n{found}"
                return ans, list({x.metadata.get('title', 'Unknown') for x in pool})

    # ---- Normal RAG flow
    per_doc_chars = 1800
    context = "\\n\\n---\\n\\n".join(d.page_content[:per_doc_chars] for d in docs)
    citations = list({d.metadata.get("title", "Unknown") for d in docs})

    if style == "short":
        style_note = "concise (150–220 words)"; max_tokens = 250
    elif style == "long":
        style_note = "detailed, well-structured (450–700 words) with short paragraphs and bullets"; max_tokens = 800
    else:
        style_note = "balanced (250–400 words)"; max_tokens = 450

    llm = ChatOpenAI(model=model, temperature=0.2, max_tokens=max_tokens)
    chain = RAG_PROMPT | llm
    ai_msg = chain.invoke({"question": query, "context": context, "style_note": style_note})
    answer_text = ai_msg.content.strip() if hasattr(ai_msg, "content") else str(ai_msg).strip()

    return answer_text, citations
