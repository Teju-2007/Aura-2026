"""retrieval.py - read uploaded notes, cut them into pieces, find the pieces that match a question.

This is a simple keyword-based form of RAG (retrieval-augmented generation: first FIND the
relevant notes, then let the AI answer using only those). It matches WORDS, not meaning,
so a question phrased very differently from your notes may miss. That is a known limit.
"""
import io
import math
import re
from collections import Counter

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "are", "was", "were", "it", "this",
    "that", "for", "on", "with", "as", "by", "at", "be", "from", "what", "how", "why", "when",
    "which", "do", "does", "did", "i", "you", "me", "my", "about", "can", "explain",
}


def tokenize(text: str):
    words = re.findall(r"\w+", text.lower())
    return [w for w in words if len(w) > 1 and w not in _STOPWORDS]


def chunk_text(text: str, size: int = 900, overlap: int = 150, max_chunks: int = 400):
    """Cut text into overlapping pieces so a sentence on a boundary is not lost."""
    text = re.sub(r"[ \t]+", " ", text).strip()
    if not text:
        return []
    chunks, start = [], 0
    while start < len(text) and len(chunks) < max_chunks:
        end = min(start + size, len(text))
        if end < len(text):  # prefer to break at a space instead of in the middle of a word
            space = text.rfind(" ", start + size // 2, end)
            end = space if space != -1 else end
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def extract_text(filename: str, data: bytes) -> str:
    """Turn an uploaded .txt / .md / .pdf file into plain text. Raises ValueError if unusable."""
    name = filename.lower()
    if name.endswith((".txt", ".md")):
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("latin-1")
    if name.endswith(".pdf"):
        from pypdf import PdfReader
        try:
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted:
                raise ValueError("This PDF is password-protected. Remove the password first.")
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        except ValueError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ValueError("This PDF could not be read.") from exc
        if not text.strip():
            raise ValueError("No readable text found. Scanned PDFs need OCR, which is not supported.")
        return text
    raise ValueError("Only .txt, .md and .pdf files are supported.")


def top_chunks(question: str, chunks, k: int = 4):
    """chunks = list of {"text","filename"}. Returns the k best matches (score > 0)."""
    query = set(tokenize(question))
    if not query or not chunks:
        return []
    token_lists = [Counter(tokenize(c["text"])) for c in chunks]
    n = len(chunks)
    doc_freq = {w: sum(1 for tl in token_lists if w in tl) for w in query}
    scored = []
    for chunk, counts in zip(chunks, token_lists):
        score = sum(counts[w] * math.log(1 + n / (1 + doc_freq[w])) for w in query if counts[w])
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [c for _, c in scored[:k]]
