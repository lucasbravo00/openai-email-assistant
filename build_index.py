"""
build_index.py: Processes the context PDF and generates the embeddings
index.

Run this script:
- The first time, before using the system
- Every time you change the context PDF

Usage:
    python build_index.py data/context.pdf
"""

import sys
import json
import importlib.util
from pathlib import Path

from openai import OpenAI


def load_module(module_name: str, file_path: str):
    """Loads a module from a file whose name starts with a number"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    if len(sys.argv) < 2:
        print("Usage: python build_index.py <path_to_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not Path(pdf_path).exists():
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)

    with open("config.json", "r") as f:
        config = json.load(f)

    pdf_processor_mod = load_module("pdf_processor", "src/01_pdf_processor.py")
    knowledge_base_mod = load_module("knowledge_base", "src/02_knowledge_base.py")

    client = OpenAI(api_key=config["openai"]["api_key"])

    print(f"📄 Processing {pdf_path}...\n")

    processor = pdf_processor_mod.PDFProcessor(
        chunk_size=config.get("rag", {}).get("chunk_size", 800),
        chunk_overlap=config.get("rag", {}).get("chunk_overlap", 150)
    )
    chunks = processor.process(pdf_path)

    if not chunks:
        print("❌ Could not extract text from the PDF. Is it a scanned PDF with no OCR?")
        sys.exit(1)

    kb = knowledge_base_mod.KnowledgeBase(
        client=client,
        index_path=config.get("rag", {}).get("index_path", "data/knowledge_index.json"),
        embedding_model=config.get("rag", {}).get("embedding_model", "text-embedding-3-small")
    )
    kb.build_index(chunks)

    print("\n✅ Done. You can now run main.py or auto_runner.py")


if __name__ == "__main__":
    main()
