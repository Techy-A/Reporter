"""Turn an uploaded policy document into numbered clauses.

Clauses are the unit of retrieval and citation ("Leave Policy §4.2"). We split on Markdown
headings, numbered headings ("4.2 Sick leave") and short ALL-CAPS lines. Long sections are cut
into paragraph-sized pieces that keep their heading, so a citation always points somewhere real.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass

MAX_CLAUSE_CHARS = 1200
MAX_DOC_BYTES = 5_000_000

_MD_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")
_NUM_HEADING = re.compile(r"^\s*(?:§\s*)?(\d{1,2}(?:\.\d{1,2}){0,3})[.)]?\s+(\S.{0,100})$")
_REF_IN_HEADING = re.compile(r"^(?:§\s*)?(\d{1,2}(?:\.\d{1,2}){0,3})[.)]?\s+(.*)$")


@dataclass
class Clause:
    ref: str
    heading: str
    text: str


class UnsupportedDocument(ValueError):
    pass


def extract_text(filename: str, data: bytes) -> str:
    """Plain text from .md / .txt / .pdf. Nothing is executed; PDFs are read with pypdf."""
    if len(data) > MAX_DOC_BYTES:
        raise UnsupportedDocument("File is larger than 5 MB")
    name = filename.lower()
    if name.endswith((".md", ".markdown", ".txt")):
        for enc in ("utf-8-sig", "cp1252"):
            try:
                return data.decode(enc)
            except UnicodeDecodeError:
                continue
        raise UnsupportedDocument("Couldn't read the file as text")
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover
            raise UnsupportedDocument("PDF support needs the pypdf package") from exc
        try:
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join((page.extract_text() or "") for page in reader.pages[:300])
        except Exception as exc:
            raise UnsupportedDocument("Couldn't read this PDF") from exc
        if len(text.strip()) < 40:
            raise UnsupportedDocument("This PDF has no readable text (is it a scan?). Upload a text PDF or .md/.txt")
        return text
    raise UnsupportedDocument("Upload a .md, .txt or .pdf file")


def _is_heading(line: str) -> tuple[str, str] | None:
    m = _MD_HEADING.match(line)
    if m:
        h = m.group(1).strip()
        r = _REF_IN_HEADING.match(h)
        return (r.group(1), r.group(2).strip()) if r else ("", h)
    m = _NUM_HEADING.match(line)
    if m and len(line.strip()) <= 90 and not line.rstrip().endswith((".", ",", ";", ":")):
        return m.group(1), m.group(2).strip()
    s = line.strip()
    if 3 <= len(s) <= 60 and s.isupper() and re.search(r"[A-Z]{3}", s):
        return "", s.title()
    return None


def split_clauses(text: str) -> list[Clause]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    sections: list[tuple[str, str, list[str]]] = []
    ref, heading, body = "", "", []
    for line in text.split("\n"):
        h = _is_heading(line)
        if h:
            if body:
                sections.append((ref, heading, body))
            ref, heading = h
            body = []
        else:
            body.append(line)
    if body:
        sections.append((ref, heading, body))

    out: list[Clause] = []
    for ref, heading, lines in sections:
        paras = [re.sub(r"\s+", " ", p).strip() for p in "\n".join(lines).split("\n\n")]
        paras = [p for p in paras if p]
        chunk = ""
        for p in paras:
            if chunk and len(chunk) + len(p) + 1 > MAX_CLAUSE_CHARS:
                out.append(Clause(ref, heading[:300], chunk))
                chunk = ""
            while len(p) > MAX_CLAUSE_CHARS:  # one giant paragraph: cut on sentence ends
                cut = p.rfind(". ", 0, MAX_CLAUSE_CHARS)
                cut = cut + 1 if cut > 200 else MAX_CLAUSE_CHARS
                out.append(Clause(ref, heading[:300], p[:cut].strip()))
                p = p[cut:].strip()
            chunk = f"{chunk} {p}".strip() if chunk else p
        if chunk:
            out.append(Clause(ref, heading[:300], chunk))
    return out
