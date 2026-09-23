import io
import logging
from typing import Tuple, Dict, Any
import pdfplumber
from fastapi import HTTPException
from config import MIN_TEXT_CHARS

logger = logging.getLogger(__name__)

class PDFParser:
    """
    Parses PDF resumes using pdfplumber.
    Extracts text and inspects layout formatting flags (tables, images, columns).
    Raises HTTPException(422) if the file contains less than MIN_TEXT_CHARS (scanned/image PDF).
    """

    @staticmethod
    def parse(file_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
        extracted_pages = []
        has_tables = False
        image_count = 0
        has_multi_column = False
        page_count = 0

        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                page_count = len(pdf.pages)
                for page in pdf.pages:
                    # 1. Text extraction
                    page_text = page.extract_text()
                    if page_text:
                        extracted_pages.append(page_text.strip())

                    # 2. Table detection
                    tables = page.extract_tables()
                    if tables and len(tables) > 0:
                        has_tables = True

                    # 3. Image detection
                    if hasattr(page, "images") and page.images:
                        image_count += len(page.images)

                    # 4. Multi-column heuristic check
                    # If words are clustered into distinct left and right horizontal buckets
                    try:
                        words = page.extract_words()
                        if words and len(words) > 30:
                            mid_x = page.width / 2
                            left_words = [w for w in words if w['x1'] < mid_x - 15]
                            right_words = [w for w in words if w['x0'] > mid_x + 15]
                            if len(left_words) > 15 and len(right_words) > 15:
                                has_multi_column = True
                    except Exception:
                        pass

        except Exception as e:
            logger.error(f"Error opening PDF with pdfplumber: {e}")
            raise HTTPException(
                status_code=422,
                detail=f"Could not parse the PDF file. It may be corrupted or password-protected: {str(e)}"
            )

        full_text = "\n\n".join(extracted_pages).strip()
        char_count = len(full_text)
        word_count = len(full_text.split())

        # Scanned / Image-based PDF check:
        # If extracted text is fewer than MIN_TEXT_CHARS (e.g. 50 characters)
        if char_count < MIN_TEXT_CHARS:
            logger.warning(f"Scanned or image-based PDF detected ({char_count} chars extracted)")
            raise HTTPException(
                status_code=422,
                detail=(
                    "Could not read this file. It appears to be an image-based or scanned PDF "
                    "without selectable text. Please upload a text-based PDF or DOCX resume."
                )
            )

        formatting_meta = {
            "file_type": "pdf",
            "page_count": page_count,
            "char_count": char_count,
            "word_count": word_count,
            "has_tables": has_tables,
            "image_count": image_count,
            "has_multi_column": has_multi_column,
        }

        return full_text, formatting_meta
