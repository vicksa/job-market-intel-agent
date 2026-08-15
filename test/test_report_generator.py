import json
from unittest.mock import MagicMock

from agent.report_generator import build_prompt, generate_report

SAMPLE_TRENDS = [
    {"skill": "python", "job_count": 42, "prev_week_count": 30, "delta": 12, "status": "up"},
    {"skill": "php", "job_count": 5, "prev_week_count": 15, "delta": -10, "status": "down"},
]


def test_build_prompt_embeds_week_and_trends():
    prompt = build_prompt(SAMPLE_TRENDS, week="2026-08-11")

    assert "2026-08-11" in prompt
    assert "python" in prompt
    assert json.dumps(SAMPLE_TRENDS, ensure_ascii=False, indent=2) in prompt


def test_generate_report_calls_claude_with_built_prompt():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Relatório semanal: Python em alta.")]
    mock_client.messages.create.return_value = mock_response

    report = generate_report(SAMPLE_TRENDS, week="2026-08-11", client=mock_client)

    assert report == "Relatório semanal: Python em alta."
    _, kwargs = mock_client.messages.create.call_args
    assert "2026-08-11" in kwargs["messages"][0]["content"]
