"""Send the weekly report to a Telegram chat via the Bot API."""
from __future__ import annotations

import os

import requests

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
REQUEST_TIMEOUT_SECONDS = 15


def send_report(text: str, bot_token: str | None = None, chat_id: str | None = None) -> dict:
    bot_token = bot_token or os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = chat_id or os.environ["TELEGRAM_CHAT_ID"]

    response = requests.post(
        TELEGRAM_API_URL.format(token=bot_token),
        json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    import sys

    send_report(sys.argv[1] if len(sys.argv) > 1 else "Teste de relatório.")
