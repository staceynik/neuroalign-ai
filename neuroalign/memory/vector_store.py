"""
Vector Store Memory
===================
Persistent user preference memory via ChromaDB.
Stores session summaries and retrieves similar past contexts.

Note: uses langchain_community.vectorstores.Chroma (not langchain_chroma,
which is a separate package that may not be installed).
"""

from pathlib import Path
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document


PERSIST_DIR = str(Path(__file__).parent.parent.parent / "data" / "chroma")
COLLECTION  = "neuroalign_memory"


def _get_store() -> Chroma:
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    return Chroma(
        collection_name=COLLECTION,
        embedding_function=embeddings,
        persist_directory=PERSIST_DIR,
    )


def retrieve_memory(query: str, k: int = 4) -> list[str]:
    """Return the k most relevant past preference strings."""
    try:
        store = _get_store()
        docs  = store.similarity_search(query, k=k)
        return [doc.page_content for doc in docs]
    except Exception:
        return []


def save_memory(text: str, metadata: dict | None = None) -> None:
    """Persist a session summary string to ChromaDB."""
    try:
        store = _get_store()
        doc   = Document(page_content=text, metadata=metadata or {})
        store.add_documents([doc])
    except Exception as e:
        print(f"[NeuroAlign] Memory save failed: {e}")
