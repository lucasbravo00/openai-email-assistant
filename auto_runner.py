"""
auto_runner.py: Runs the classification + reply generation pipeline in
a loop, checking the inbox every N minutes.

Usage:
    python auto_runner.py
    (or better, in the background with start_auto_runner.sh)
"""

import json
import time
import importlib.util
from datetime import datetime


def load_module(module_name: str, file_path: str):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_cycle(outlook, kb, generator, config):
    """Runs a single inbox-check cycle"""
    emails = outlook.get_unread_emails(max_count=config.get("max_emails_per_run", 10))

    if not emails:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📭 No new emails")
        return

    for email in emails:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📨 {email['subject']} (from {email['sender_name']})")

        query = f"{email['subject']} {email['body']}"
        relevant_chunks = kb.search(query, top_k=config.get("rag", {}).get("top_k", 4))

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


def main():
    from openai import OpenAI

    with open("config.json", "r") as f:
        config = json.load(f)

    knowledge_base_mod = load_module("knowledge_base", "src/02_knowledge_base.py")
    email_generator_mod = load_module("email_generator", "src/03_email_generator.py")
    outlook_mod = load_module("outlook_connector", "src/04_outlook_connector.py")

    client = OpenAI(api_key=config["openai"]["api_key"])

    kb = knowledge_base_mod.KnowledgeBase(
        client=client,
        index_path=config.get("rag", {}).get("index_path", "data/knowledge_index.json"),
        embedding_model=config.get("rag", {}).get("embedding_model", "text-embedding-3-small")
    )
    if not kb.load_index():
        print("❌ No index has been built yet.")
        print("   Run this first: python build_index.py <path_to_pdf>")
        return

    generator = email_generator_mod.EmailGenerator(
        client=client,
        model=config["openai"].get("chat_model", "gpt-4o-mini")
    )

    outlook = outlook_mod.OutlookConnector(
        client_id=config["outlook"]["client_id"],
        tenant_id=config["outlook"].get("tenant_id", "consumers")
    )

    if not outlook.authenticate():
        print("❌ Could not authenticate with Outlook.")
        return

    interval_minutes = config.get("check_interval_minutes", 10)
    print(f"🚀 Auto runner started. Checking every {interval_minutes} minutes.")

    while True:
        try:
            run_cycle(outlook, kb, generator, config)
        except Exception as e:
            print(f"❌ Error during cycle: {str(e)}")

        time.sleep(interval_minutes * 60)


if __name__ == "__main__":
    main()
