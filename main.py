"""
main.py: Runs a single cycle of classification + reply generation for
the unread emails in the inbox.

Usage:
    python main.py
"""

import json
import importlib.util

from openai import OpenAI


def load_module(module_name: str, file_path: str):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    with open("config.json", "r") as f:
        config = json.load(f)

    knowledge_base_mod = load_module("knowledge_base", "src/02_knowledge_base.py")
    email_generator_mod = load_module("email_generator", "src/03_email_generator.py")
    outlook_mod = load_module("outlook_connector", "src/04_outlook_connector.py")

    client = OpenAI(api_key=config["openai"]["api_key"])

    # --- Load the knowledge base (RAG) ---
    kb = knowledge_base_mod.KnowledgeBase(
        client=client,
        index_path=config.get("rag", {}).get("index_path", "data/knowledge_index.json"),
        embedding_model=config.get("rag", {}).get("embedding_model", "text-embedding-3-small")
    )
    if not kb.load_index():
        print("❌ No index has been built yet.")
        print("   Run this first: python build_index.py <path_to_pdf>")
        return

    # --- Reply generator ---
    generator = email_generator_mod.EmailGenerator(
        client=client,
        model=config["openai"].get("chat_model", "gpt-4o-mini")
    )

    # --- Outlook connector ---
    outlook = outlook_mod.OutlookConnector(
        client_id=config["outlook"]["client_id"],
        tenant_id=config["outlook"].get("tenant_id", "consumers")
    )

    if not outlook.authenticate():
        print("❌ Could not authenticate with Outlook.")
        return

    emails = outlook.get_unread_emails(max_count=config.get("max_emails_per_run", 10))

    if not emails:
        print("📭 No new emails to process.")
        return

    for email in emails:
        print(f"\n{'=' * 60}")
        print(f"📨 Processing: {email['subject']} (from {email['sender_name']})")

        # Retrieve relevant context from the PDF
        query = f"{email['subject']} {email['body']}"
        relevant_chunks = kb.search(query, top_k=config.get("rag", {}).get("top_k", 4))

        # Generate the reply body
        reply_body = generator.generate_reply(
            email_subject=email["subject"],
            email_body=email["body"],
            sender_name=email["sender_name"],
            retrieved_chunks=relevant_chunks
        )

        draft = {
            "to": email["sender"],
            "subject": f"RE: {email['subject']}",
            "body": reply_body
        }

        outlook.save_as_draft(draft)
        outlook.mark_as_read(email["id"])

    print(f"\n{'=' * 60}")
    print(f"✅ Processed {len(emails)} emails. Review the drafts in Outlook before sending them.")


if __name__ == "__main__":
    main()
