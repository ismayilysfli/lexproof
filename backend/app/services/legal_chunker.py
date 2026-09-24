import re
from typing import Dict, List, Optional


ARTICLE_PATTERNS = [
    re.compile(
        r"^Article\s+\d+[A-Za-z]?[.]?$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^Madd\u0259\s+\d+[A-Za-z]?[.]?$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:\u010Clan|Clan)\s+\d+[A-Za-z]?[.]?$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^Artikel\s+\d+[A-Za-z]?[.]?$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\u00A7\s*\d+[A-Za-z]?$",
        re.IGNORECASE,
    ),
]


SECTION_PATTERN = re.compile(
    r"^Section\s+\d+[A-Za-z]?[.]?$",
    re.IGNORECASE,
)


CHAPTER_PATTERN = re.compile(
    r"^CHAPTER\s+(?:\d+|[IVXLCDM]+)[.]?$"
)


def _normalize_line(line: str) -> str:
    return " ".join(line.strip().split())


def _is_article_heading(line: str) -> bool:
    normalized = _normalize_line(line)

    return any(
        pattern.fullmatch(normalized)
        for pattern in ARTICLE_PATTERNS
    )


def _extract_article_number(line: str) -> Optional[int]:
    match = re.search(r"\d+", line)

    if not match:
        return None

    return int(match.group())


def _is_section_heading(line: str) -> bool:
    return bool(
        SECTION_PATTERN.fullmatch(
            _normalize_line(line)
        )
    )


def _is_chapter_heading(line: str) -> bool:
    return bool(
        CHAPTER_PATTERN.fullmatch(
            _normalize_line(line)
        )
    )


def _fallback_page_chunks(
    pages: List[Dict],
    max_chars: int = 2500,
) -> List[Dict]:
    chunks = []

    for page in pages:
        text = page["text"].strip()

        if not text:
            continue

        start = 0
        part = 1

        while start < len(text):
            chunk_text = text[
                start:start + max_chars
            ].strip()

            if chunk_text:
                chunks.append({
                    "chunk_id": (
                        f"page-{page['page_number']}"
                        f"-part-{part}"
                    ),
                    "heading": None,
                    "section": None,
                    "chapter": None,
                    "page_start": page["page_number"],
                    "page_end": page["page_number"],
                    "text": chunk_text,
                })

            start += max_chars
            part += 1

    return chunks


def chunk_legal_document(
    pages: List[Dict],
) -> Dict:
    chunks = []

    current_heading = None
    current_lines = []
    current_start_page = None
    current_end_page = None

    current_section = None
    current_chapter = None

    article_section = None
    article_chapter = None

    last_article_number = None
    sequential_mode = False

    def save_current_chunk():
        nonlocal current_heading
        nonlocal current_lines
        nonlocal current_start_page
        nonlocal current_end_page
        nonlocal article_section
        nonlocal article_chapter

        if not current_heading:
            return

        text = "\n".join(
            current_lines
        ).strip()

        if not text:
            return

        chunks.append({
            "chunk_id": (
                f"article-{len(chunks) + 1}"
            ),
            "heading": current_heading,
            "section": article_section,
            "chapter": article_chapter,
            "page_start": current_start_page,
            "page_end": current_end_page,
            "text": text,
        })

    for page in pages:
        page_number = page["page_number"]

        for raw_line in page["text"].splitlines():
            line = _normalize_line(raw_line)

            if not line:
                continue

            # Structural headings are metadata,
            # not standalone evidence chunks.
            if _is_chapter_heading(line):
                current_chapter = line
                current_section = None
                continue

            if _is_section_heading(line):
                current_section = line
                continue

            if _is_article_heading(line):
                article_number = (
                    _extract_article_number(line)
                )

                if article_number is None:
                    continue

                # Full statutes normally begin with
                # Article 1. If they do, require articles
                # to continue sequentially.
                if last_article_number is None:
                    sequential_mode = (
                        article_number == 1
                    )

                elif (
                    sequential_mode
                    and article_number
                    != last_article_number + 1
                ):
                    # Likely a citation/reference such as
                    # "Article 63." appearing on its own
                    # extracted PDF line.
                    if current_heading:
                        current_lines.append(line)
                        current_end_page = page_number

                    continue

                save_current_chunk()

                current_heading = line
                current_lines = [line]

                current_start_page = page_number
                current_end_page = page_number

                article_section = current_section
                article_chapter = current_chapter

                last_article_number = article_number

                continue

            if current_heading:
                current_lines.append(line)
                current_end_page = page_number

    save_current_chunk()

    if chunks:
        return {
            "strategy": "article",
            "chunk_count": len(chunks),
            "chunks": chunks,
        }

    fallback_chunks = _fallback_page_chunks(
        pages
    )

    return {
        "strategy": "page_fallback",
        "chunk_count": len(fallback_chunks),
        "chunks": fallback_chunks,
    }

