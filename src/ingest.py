import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

load_dotenv()

PDF_DIR = "data/pdfs"
INDEX_DIR = "data/index/faiss"
os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(INDEX_DIR, exist_ok=True)

def build_index():
    """Load PDFs, split text, create embeddings and save FAISS index."""
    pdf_files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print("❌ No PDFs found in data/pdfs folder.")
        return

    docs = []
    for file in pdf_files:
        path = os.path.join(PDF_DIR, file)
        print(f"📘 Loading {file}...")
        loader = PyPDFLoader(path)
        pages = loader.load()
        for p in pages:
            p.metadata["title"] = file
        docs.extend(pages)

    # Smaller chunks => cheaper context to the LLM
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
    chunks = splitter.split_documents(docs)
    print(f"✅ Created {len(chunks)} chunks total.")

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vs = FAISS.from_documents(chunks, embeddings)
    vs.save_local(INDEX_DIR)
    print(f"✅ Saved FAISS index at {INDEX_DIR}")

if __name__ == "__main__":
    build_index()
