import pymupdf


def extract_pdf_text(pdf_bytes: bytes) -> dict:
    document = pymupdf.open(
        stream=pdf_bytes,
        filetype="pdf"
    )

    pages = []
    total_text = []

    for page_number, page in enumerate(document, start=1):
        text = page.get_text("text").strip()

        pages.append({
            "page_number": page_number,
            "text": text
        })

        if text:
            total_text.append(text)

    document.close()

    full_text = "\n\n".join(total_text)

    return {
        "page_count": len(pages),
        "character_count": len(full_text),
        "text": full_text,
        "pages": pages
    }
