import re
from typing import List, Dict


ARTICLE_PATTERN = re.compile(
    r"^\s*("
    r"Article\s+\d+[A-Za-z\-]*\.?"
    r"|Section\s+\d+[A-Za-z\-]*\.?"
    r"|Madd\u0259\s+\d+[A-Za-z\-]*\.?"
    r"|\u010Clan\s+\d+[A-Za-z\-]*\.?"
    r"|Clan\s+\d+[A-Za-z\-]*\.?"
    r"|Artikel\s+\d+[A-Za-z\-]*\.?"
    r"|\u00A7\s*\d+[A-Za-z\-]*"
    r")",
    re.IGNORECASE,
)


def _is_article_heading(line: str) -> bool:
    return bool(ARTICLE_PATTERN.match(line.strip()))


def _fallback_page_chunks(
    pages: List[Dict],
    max_chars: int = 2500
) -> List[Dict]:
    chunks = []

    for page in pages:
        text = page["text"].strip()

        if not text:
            continue

        start = 0
        part = 1

        while start < len(text):
            chunk_text = text[start:start + max_chars].strip()

            if chunk_text:
                chunks.append({
                    "chunk_id": f"page-{page['page_number']}-part-{part}",
                    "heading": None,
                    "page_start": page["page_number"],
                    "page_end": page["page_number"],
                    "text": chunk_text,
                })

            start += max_chars
            part += 1

    return chunks


def chunk_legal_document(pages: List[Dict]) -> Dict:
    chunks = []

    current_heading = None
    current_lines = []
    current_start_page = None
    current_end_page = None

    def save_current_chunk():
        nonlocal current_heading
        nonlocal current_lines
        nonlocal current_start_page
        nonlocal current_end_page

        text = "\n".join(current_lines).strip()

        if current_heading and text:
            chunks.append({
                "chunk_id": f"article-{len(chunks) + 1}",
                "heading": current_heading,
                "page_start": current_start_page,
                "page_end": current_end_page,
                "text": text,
            })

    for page in pages:
        page_number = page["page_number"]
        lines = page["text"].splitlines()

        for raw_line in lines:
            line = raw_line.strip()

            if not line:
                continue

            if _is_article_heading(line):
                save_current_chunk()

                current_heading = line
                current_lines = [line]
                current_start_page = page_number
                current_end_page = page_number

            elif current_heading:
                current_lines.append(line)
                current_end_page = page_number

    save_current_chunk()

    if chunks:
        return {
            "strategy": "article",
            "chunk_count": len(chunks),
            "chunks": chunks,
        }

    fallback_chunks = _fallback_page_chunks(pages)

    return {
        "strategy": "page_fallback",
        "chunk_count": len(fallback_chunks),
        "chunks": fallback_chunks,
    }
