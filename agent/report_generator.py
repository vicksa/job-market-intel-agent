"""Turn gold-layer weekly trends into a natural-language report via an LLM."""
from __future__ import annotations

import json
import os
from pathlib import Path

import anthropic

PROMPT_PATH = Path(__file__).parent / "prompts" / "weekly_report.txt"
MODEL = os.environ.get("REPORT_MODEL", "claude-sonnet-5")


def load_prompt_template(path: Path = PROMPT_PATH) -> str:
    return path.read_text(encoding="utf-8")


def build_prompt(trends: list[dict], week: str, template: str | None = None) -> str:
    template = template or load_prompt_template()
    return template.format(
        week=week, trends_json=json.dumps(trends, ensure_ascii=False, indent=2)
    )


def generate_report(
    trends: list[dict], week: str, client: anthropic.Anthropic | None = None
) -> str:
    client = client or anthropic.Anthropic()
    prompt = build_prompt(trends, week)
    message = client.messages.create(
        model=MODEL,
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


if __name__ == "__main__":
    import sys

    gold_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("gold_trends.json")
    week_arg = sys.argv[2] if len(sys.argv) > 2 else "current"
    trends_data = json.loads(gold_path.read_text(encoding="utf-8"))
    print(generate_report(trends_data, week_arg))
