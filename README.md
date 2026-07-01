# 📧 Email Assistant with OpenAI + RAG over a PDF

System that reads unread emails from your Outlook inbox, searches for
relevant context inside a PDF (manual, policies, FAQ, etc.) and uses the
OpenAI API (GPT) to draft a reply, ready for you to review before
sending it.

Unlike a classifier trained with scikit-learn, there is **no training
step** here: the PDF is the only knowledge source, and GPT generates
the text dynamically for each email, using the most relevant fragments
of the PDF for that specific query (a technique called **RAG**:
Retrieval-Augmented Generation).

## 🏗️ Project structure

```
openai-email-assistant/
├── config.example.json          # Configuration template
├── requirements.txt
├── build_index.py               # Processes the PDF and generates embeddings
├── main.py                      # Runs a single cycle
├── auto_runner.py               # Runs in a loop every N minutes
├── src/
│   ├── 01_pdf_processor.py      # Extracts and chunks the PDF text
│   ├── 02_knowledge_base.py     # Embeddings + semantic search (RAG)
│   ├── 03_email_generator.py    # GPT calls for classifying/drafting
│   └── 04_outlook_connector.py  # Reads inbox and saves drafts (Graph API)
├── data/                        # PDF, embeddings index, tokens (not versioned)
└── install_dependencies.sh
```

## 🚀 Installation

### 1. Install dependencies
```bash
bash install_dependencies.sh
```

### 2. Set up credentials
```bash
cp config.example.json config.json
```
Edit `config.json` and fill in:
- `openai.api_key`: your OpenAI API key ([platform.openai.com](https://platform.openai.com/api-keys))
- `outlook.client_id`: the CLIENT_ID of an app registered in [Azure Portal](https://portal.azure.com)
  (with `Mail.Read` and `Mail.ReadWrite` permissions)

**`config.json` is never committed to the repo** (it's in `.gitignore`).

### 3. Index your context PDF
```bash
python build_index.py path/to/your_manual.pdf
```
This extracts the text, splits it into fragments and generates
embeddings with `text-embedding-3-small`, saving everything to
`data/knowledge_index.json`. Re-run this command every time you update
the PDF.

### 4. Authenticate with Outlook (first time)
The first time you run `main.py` or `auto_runner.py`, a browser window
will open so you can log in with your Outlook account. The token is
saved locally (`data/token_cache.json`) so you don't have to log in
again.

## ▶️ Usage

**Run once** (processes unread emails and exits):
```bash
python main.py
```

**Run in a loop** (checks the inbox every `check_interval_minutes`):
```bash
bash start_auto_runner.sh
tail -f data/auto_runner.log   # view activity
bash stop_auto_runner.sh       # stop it
```

## 🔍 How the RAG works

1. `build_index.py` extracts the PDF text, splits it into ~800-character
   fragments with overlap, and asks the OpenAI embeddings API for a
   numeric vector per fragment.
2. When a new email arrives, its embedding is generated and compared
   (cosine similarity) against every fragment of the PDF.
3. The `top_k` most similar fragments are selected and passed to GPT as
   context inside the prompt, along with tone/style instructions.
4. GPT drafts the reply based **only** on that context (avoiding making
   up information that isn't in the PDF).

## ⚠️ Security notes

- The draft is saved in Outlook but **never sent automatically**; it
  always requires human review before sending.
- `config.json`, the embeddings index and the token cache are excluded
  from version control via `.gitignore`.
- Your OpenAI key and Azure `client_id` stay only on your machine.

## 💰 Approximate costs

- **Indexing the PDF**: paid once (or every time you update it).
  `text-embedding-3-small` costs cents even for long PDFs.
- **Per email**: 1 embedding (query) + 1 chat completion call.
  With `gpt-4o-mini`, the cost per email is usually a fraction of a cent.
