#!/bin/bash
# Run this once to install all required dependencies
# Usage: bash install_dependencies.sh

echo "======================================"
echo "Installing Email Assistant Dependencies"
echo "======================================"

pip install --upgrade pip
pip install openai            # OpenAI API (chat + embeddings)
pip install numpy             # Cosine similarity for the RAG
pip install pdfplumber        # PDF text extraction
pip install msal              # Microsoft Authentication Library (Outlook)
pip install requests          # HTTP requests

echo ""
echo "======================================"
echo "✅ All dependencies installed!"
echo "======================================"
echo ""
echo "Next steps:"
echo "  1. cp config.example.json config.json  (and fill in your keys)"
echo "  2. python build_index.py <path_to_pdf>"
echo "  3. python main.py"
