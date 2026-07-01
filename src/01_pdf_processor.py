"""
PDF Processor: Extracts text from a context PDF and splits it into
chunks ready for embedding generation.

Uses pdfplumber (better layout extraction than pypdf) and does simple
character-based chunking with overlap, which works well for running
text (manuals, policies, FAQs, etc.)
"""

import re
from typing import List, Dict
from dataclasses import dataclass

import pdfplumber


@dataclass
class Chunk:
    """A piece of text from the PDF with metadata"""
    id: int
    text: str
    page: int


class PDFProcessor:
    """Extracts and chunks text from a PDF to use as a knowledge base"""

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        """
        Args:
            chunk_size: Approximate size of each chunk, in characters
            chunk_overlap: How many characters overlap between consecutive
                           chunks (avoids cutting ideas in half)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def extract_text_by_page(self, pdf_path: str) -> List[Dict]:
        """
        Extracts the text of each page in the PDF

        Args:
            pdf_path: Path to the PDF file

        Returns:
            List of dicts {"page": int, "text": str}
        """
        pages = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    pages.append({"page": i + 1, "text": text})
        except Exception as e:
            print(f"❌ Error reading PDF: {str(e)}")
            return []

        print(f"✅ Extracted {len(pages)} pages from {pdf_path}")
        return pages

    def _clean_text(self, text: str) -> str:
        """Normalizes whitespace and odd line breaks"""
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def chunk_text(self, pages: List[Dict]) -> List[Chunk]:
        """
        Splits the text of all pages into overlapping chunks

        Args:
            pages: Output of extract_text_by_page()

        Returns:
            List of Chunk objects
        """
        chunks = []
        chunk_id = 0

        for page_data in pages:
            text = self._clean_text(page_data["text"])
            if not text:
                continue

            start = 0
            while start < len(text):
                end = start + self.chunk_size
                chunk_text = text[start:end]

                chunks.append(Chunk(
                    id=chunk_id,
                    text=chunk_text,
                    page=page_data["page"]
                ))
                chunk_id += 1

                # Advance leaving the overlap
                start += self.chunk_size - self.chunk_overlap

        print(f"✅ Generated {len(chunks)} text chunks")
        return chunks

    def process(self, pdf_path: str) -> List[Chunk]:
        """
        Full pipeline: extract + chunk

        Args:
            pdf_path: Path to the context PDF

        Returns:
            List of chunks ready for embedding generation
        """
        pages = self.extract_text_by_page(pdf_path)
        if not pages:
            return []
        return self.chunk_text(pages)
