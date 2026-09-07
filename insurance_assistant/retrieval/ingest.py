"""Ingesta de la póliza a ChromaDB: PDF -> texto por página -> chunks -> vectores.

Uso:  python -m insurance_assistant.retrieval.ingest
"""
from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

from insurance_assistant.documents.loaders import load_pdf_pages
from insurance_assistant.retrieval.vectorstore import get_client, get_collection
from insurance_assistant.settings import settings


def ingest(reset: bool = True) -> int:
    """Indexa los PDF de data/policy. Devuelve el número de chunks."""
    collection = get_collection()

    if reset and collection.count() > 0:
        get_client().delete_collection(collection.name)
        collection = get_collection()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    docs, metas, ids = [], [], []
    pdfs = sorted(settings.policy_dir.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"No hay PDF en {settings.policy_dir}")

    for pdf in pdfs:
        for page_num, text in load_pdf_pages(pdf):
            for j, chunk in enumerate(splitter.split_text(text)):
                docs.append(chunk)
                metas.append({"source": pdf.name, "page": page_num})
                ids.append(f"{pdf.stem}-p{page_num}-c{j}")

    for start in range(0, len(docs), 100):
        end = start + 100
        collection.add(
            documents=docs[start:end],
            metadatas=metas[start:end],
            ids=ids[start:end],
        )

    return len(docs)


if __name__ == "__main__":
    n = ingest()
    print(f"Ingesta completa: {n} chunks indexados en ChromaDB.")
