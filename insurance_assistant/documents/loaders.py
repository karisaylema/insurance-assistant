"""Carga y lectura de documentos (póliza y claims)."""
from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path

from pypdf import PdfReader

from insurance_assistant.settings import settings


def load_pdf_pages(path: Path) -> list[tuple[int, str]]:
    """[(num_pagina, texto), ...] saltando portadas y páginas en blanco."""
    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if len(text) > 40:
            pages.append((i, text))
    return pages


@lru_cache(maxsize=1)
def load_policy_text() -> str:
    """Póliza completa como un solo texto con marcadores de página (modo CAG)."""
    return _format_pages(policy_page_map().items())


@lru_cache(maxsize=1)
def policy_page_map() -> dict[tuple[str, int], str]:
    """Mapa {(archivo, pág.): texto} de todas las páginas de la póliza.
    Lo usa el modo híbrido para cargar páginas completas por número."""
    pages: dict[tuple[str, int], str] = {}
    for pdf in sorted(settings.policy_dir.glob("*.pdf")):
        for page_num, text in load_pdf_pages(pdf):
            pages[(pdf.name, page_num)] = text
    return pages


def load_pages(keys: list[tuple[str, int]]) -> str:
    """Devuelve el texto COMPLETO de las páginas indicadas (modo híbrido)."""
    page_map = policy_page_map()
    return _format_pages((k, page_map[k]) for k in keys if k in page_map)


def _format_pages(items) -> str:
    return "\n\n".join(
        f"[{source} · pág. {page}]\n{text}" for (source, page), text in items
    )


def read_document(data: bytes, filename: str) -> str:
    """Convierte los bytes de un archivo subido a texto plano."""
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((p.extract_text() or "") for p in reader.pages)

    if suffix == ".docx":
        import docx

        doc = docx.Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)

    return data.decode("utf-8", errors="ignore")
