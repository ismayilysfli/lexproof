from typing import Dict, List

import json
import logging
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import BadZipFile

import numpy as np
from sentence_transformers import SentenceTransformer


MODEL_NAME = "intfloat/multilingual-e5-small"
CACHE_VERSION = 1  # Bump when passage construction or embedding settings change.
DEFAULT_INDEX_PATH = Path(__file__).resolve().parents[3] / "data/indexes/retrieval.npz"
logger = logging.getLogger(__name__)

_model = None
_embeddings = None
_title_embeddings = None

_entries: List[Dict] = []
_article_titles: Dict[str, str] = {}

_document_name = None


def _index_path() -> Path:
    return Path(os.environ.get("LEXPROOF_INDEX_PATH", DEFAULT_INDEX_PATH))


def _save_index() -> None:
    path = _index_path()
    temporary_path = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        metadata = {
            "version": CACHE_VERSION,
            "model": MODEL_NAME,
            "document": _document_name,
            "entries": _entries,
            "article_titles": {
                heading: data["title"] for heading, data in _article_titles.items()
            },
        }
        # One atomic file prevents a partial write from replacing a working cache.
        with NamedTemporaryFile(dir=path.parent, suffix=".npz", delete=False) as stream:
            temporary_path = Path(stream.name)
            np.savez_compressed(
                stream,
                metadata=np.array(json.dumps(metadata, ensure_ascii=False)),
                embeddings=_embeddings,
                # Documents without article headings have an empty title matrix.
                title_embeddings=_title_embeddings.reshape(
                    len(_article_titles), _embeddings.shape[1]
                ),
            )
        os.replace(temporary_path, path)
    except OSError as exc:
        logger.warning("Unable to save retrieval index to %s: %s", path, exc)
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError as exc:
                logger.warning("Unable to remove temporary index %s: %s", temporary_path, exc)


def load_cached_index() -> bool:
    """Restore the last indexed document without loading an embedding model."""
    global _embeddings, _title_embeddings, _entries, _article_titles, _document_name

    path = _index_path()
    try:
        # Metadata is JSON; never deserialize pickled Python objects from disk.
        with np.load(path, allow_pickle=False) as cached:
            metadata = json.loads(str(cached["metadata"].item()))
            embeddings = cached["embeddings"]
            title_embeddings = cached["title_embeddings"]
        if metadata["version"] != CACHE_VERSION or metadata["model"] != MODEL_NAME:
            raise ValueError("Index version or embedding model has changed; rebuild the index.")
        entries = metadata["entries"]
        titles = metadata["article_titles"]
        document = metadata["document"]
        if not isinstance(document, str) or not isinstance(entries, list) or not entries:
            raise ValueError("Invalid index metadata.")
        if not isinstance(titles, dict) or not all(isinstance(title, str) for title in titles.values()):
            raise ValueError("Invalid article titles.")
        required_fields = {"document", "heading", "title", "chapter", "section",
                           "page_start", "page_end", "segment_number", "text"}
        for entry in entries:
            if (
                not isinstance(entry, dict)
                or not required_fields.issubset(entry)
                or entry["document"] != document
                or not isinstance(entry["text"], str)
                or not isinstance(entry["title"], str)
                or (entry["heading"] is not None and entry["heading"] not in titles)
            ):
                raise ValueError("Invalid passage metadata.")
        if (
            embeddings.ndim != 2
            or embeddings.shape[0] != len(entries)
            or embeddings.shape[1] != 384  # multilingual-e5-small output dimension
            or title_embeddings.shape != (len(titles), 384)
            or not np.issubdtype(embeddings.dtype, np.floating)
            or not np.issubdtype(title_embeddings.dtype, np.floating)
            or not np.isfinite(embeddings).all()
            or not np.isfinite(title_embeddings).all()
        ):
            raise ValueError("Invalid index embedding arrays.")
        article_titles = {
            heading: {"title": title, "embedding": title_embeddings[index]}
            for index, (heading, title) in enumerate(titles.items())
        }
    except FileNotFoundError:
        return False
    except (OSError, ValueError, KeyError, TypeError, AttributeError, EOFError, BadZipFile) as exc:
        logger.warning("Unable to load retrieval index from %s: %s", path, exc)
        return False

    # Publish only after the complete cache has passed validation.
    _entries = entries
    _embeddings = embeddings
    _title_embeddings = title_embeddings
    _article_titles = article_titles
    _document_name = document
    logger.info("Restored retrieval index for %s from %s", document, path)
    return True


def _get_model():
    global _model

    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)

    return _model


def _split_text(
    text: str,
    max_chars: int = 1400,
    overlap: int = 200,
) -> List[str]:
    text = " ".join(text.split())

    if len(text) <= max_chars:
        return [text]

    parts = []
    start = 0

    while start < len(text):
        end = min(
            start + max_chars,
            len(text),
        )

        if end < len(text):
            sentence_break = text.rfind(
                ". ",
                start,
                end,
            )

            if sentence_break > (
                start + max_chars // 2
            ):
                end = sentence_break + 1

        part = text[start:end].strip()

        if part:
            parts.append(part)

        if end >= len(text):
            break

        start = max(
            0,
            end - overlap,
        )

    return parts


def _extract_article_title(
    text: str,
    heading: str | None,
) -> str:
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if not lines:
        return heading or ""

    if heading and lines[0].lower() == heading.lower():
        lines = lines[1:]

    if not lines:
        return heading or ""

    title = lines[0]

    if heading:
        return f"{heading}: {title}"

    return title


def index_chunks(
    chunks: List[Dict],
    document_name: str,
) -> Dict:
    global _embeddings
    global _title_embeddings
    global _entries
    global _article_titles
    global _document_name

    model = _get_model()

    entries = []
    passages = []

    article_titles = {}
    title_inputs = []

    for chunk in chunks:
        heading = chunk.get("heading")

        title = _extract_article_title(
            chunk["text"],
            heading,
        )

        if heading:
            article_titles[heading] = title

        segments = _split_text(
            chunk["text"]
        )

        for segment_number, segment in enumerate(
            segments,
            start=1,
        ):
            entry = {
                "document": document_name,
                "heading": heading,
                "title": title,
                "chapter": chunk.get("chapter"),
                "section": chunk.get("section"),
                "page_start": chunk.get("page_start"),
                "page_end": chunk.get("page_end"),
                "segment_number": segment_number,
                "text": segment,
            }

            entries.append(entry)

            passages.append(
                f"passage: {segment}"
            )

    ordered_headings = list(
        article_titles.keys()
    )

    for heading in ordered_headings:
        title_inputs.append(
            "passage: "
            + article_titles[heading]
        )

    embeddings = model.encode(
        passages,
        batch_size=16,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    title_embeddings = model.encode(
        title_inputs,
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    _entries = entries
    _embeddings = embeddings

    _article_titles = {
        heading: {
            "title": article_titles[heading],
            "embedding": title_embeddings[index],
        }
        for index, heading in enumerate(
            ordered_headings
        )
    }

    _title_embeddings = title_embeddings
    _document_name = document_name
    _save_index()

    return {
        "document": document_name,
        "article_count": len(chunks),
        "passage_count": len(entries),
        "embedding_dimension": int(
            embeddings.shape[1]
        ),
        "model": MODEL_NAME,
    }


def search_index(
    query: str,
    top_k: int = 5,
) -> Dict:
    if _embeddings is None or not _entries:
        raise RuntimeError(
            "No document has been indexed yet."
        )

    model = _get_model()

    query_embedding = model.encode(
        [f"query: {query}"],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )[0]

    passage_scores = np.dot(
        _embeddings,
        query_embedding,
    )

    candidate_count = min(
        len(_entries),
        max(top_k * 12, 30),
    )

    ranked_indexes = np.argsort(
        -passage_scores
    )[:candidate_count]

    article_results = {}

    for index in ranked_indexes:
        index = int(index)

        entry = _entries[index]
        heading = entry["heading"]

        if not heading:
            continue

        passage_score = float(
            passage_scores[index]
        )

        title_data = _article_titles.get(
            heading
        )

        title_score = 0.0

        if title_data is not None:
            title_score = float(
                np.dot(
                    title_data["embedding"],
                    query_embedding,
                )
            )

        # Passage meaning is still dominant,
        # but the article's own title helps
        # distinguish primary law from references.
        combined_score = passage_score

        existing = article_results.get(
            heading
        )

        if (
            existing is None
            or combined_score
            > existing["combined_score"]
        ):
            article_results[heading] = {
                "combined_score": combined_score,
                "passage_score": passage_score,
                "title_score": title_score,
                "entry": entry,
            }

    ranked_articles = sorted(
        article_results.values(),
        key=lambda item: item[
            "combined_score"
        ],
        reverse=True,
    )

    results = []

    for item in ranked_articles[:top_k]:
        entry = item["entry"]

        results.append({
            "score": round(
                item["combined_score"],
                4,
            ),
            "passage_score": round(
                item["passage_score"],
                4,
            ),
            "title_score": round(
                item["title_score"],
                4,
            ),
            **entry,
        })

    return {
        "query": query,
        "document": _document_name,
        "result_count": len(results),
        "results": results,
    }



def search_passages(
    query: str,
    top_k: int = 8,
) -> Dict:
    if _embeddings is None or not _entries:
        raise RuntimeError(
            "No document has been indexed yet."
        )

    model = _get_model()

    query_embedding = model.encode(
        [f"query: {query}"],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )[0]

    scores = np.dot(
        _embeddings,
        query_embedding,
    )

    result_count = min(
        top_k,
        len(_entries),
    )

    ranked_indexes = np.argsort(
        -scores
    )[:result_count]

    results = []

    for index in ranked_indexes:
        index = int(index)
        entry = _entries[index]

        results.append({
            "retrieval_score": round(
                float(scores[index]),
                4,
            ),
            **entry,
        })

    return {
        "query": query,
        "document": _document_name,
        "result_count": len(results),
        "results": results,
    }
