"""Document ingestion — PDF / DOCX / TXT -> text chunks with per-page provenance.

Deterministic and offline (no model). Every chunk carries ``doc_id`` + ``page`` so the
provenance survives chunking and can be threaded all the way to a Finding's evidence.
PDF page numbers are 1-based; DOCX has no real pages, so paragraphs are bucketed into
synthetic "pages" of a fixed paragraph count purely to preserve a stable locator.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_DOCX_PARAS_PER_PAGE = 15


@dataclass
class Chunk:
    doc_id: str
    page: int
    text: str


def _ingest_pdf(path: Path, doc_id: str) -> list[Chunk]:
    from pypdf import PdfReader  # imported lazily so the core has no hard dep

    reader = PdfReader(str(path))
    chunks: list[Chunk] = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            chunks.append(Chunk(doc_id=doc_id, page=i, text=text))
    return chunks


def _ingest_docx(path: Path, doc_id: str) -> list[Chunk]:
    import docx  # python-docx

    document = docx.Document(str(path))
    paras = [p.text for p in document.paragraphs if p.text and p.text.strip()]
    chunks: list[Chunk] = []
    for start in range(0, len(paras), _DOCX_PARAS_PER_PAGE):
        page = start // _DOCX_PARAS_PER_PAGE + 1
        text = "\n".join(paras[start:start + _DOCX_PARAS_PER_PAGE]).strip()
        if text:
            chunks.append(Chunk(doc_id=doc_id, page=page, text=text))
    return chunks


def _ingest_txt(path: Path, doc_id: str) -> list[Chunk]:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    return [Chunk(doc_id=doc_id, page=1, text=text)] if text else []


def ingest_file(path: str | Path, doc_id: str | None = None) -> list[Chunk]:
    """Ingest one document into page-tagged chunks. doc_id defaults to the filename."""
    p = Path(path)
    doc_id = doc_id or p.name
    suffix = p.suffix.lower()
    if suffix == ".pdf":
        return _ingest_pdf(p, doc_id)
    if suffix == ".docx":
        return _ingest_docx(p, doc_id)
    if suffix in (".txt", ".md"):
        return _ingest_txt(p, doc_id)
    raise ValueError(f"unsupported document type: {suffix!r} (use .pdf, .docx, .txt, .md)")


def ingest_bytes(data: bytes, filename: str, doc_id: str | None = None) -> list[Chunk]:
    """Ingest raw bytes (e.g. an uploaded file) by writing to a temp file."""
    import tempfile

    doc_id = doc_id or filename
    suffix = Path(filename).suffix.lower() or ".txt"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    try:
        return ingest_file(tmp_path, doc_id=doc_id)
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass


def chunks_to_prompt_block(chunks: list[Chunk], max_chars: int = 24000) -> str:
    """Render chunks into a provenance-tagged text block for the extraction prompt."""
    parts: list[str] = []
    total = 0
    for c in chunks:
        block = f"[doc_id={c.doc_id} page={c.page}]\n{c.text}\n"
        if total + len(block) > max_chars:
            break
        parts.append(block)
        total += len(block)
    return "\n".join(parts)
