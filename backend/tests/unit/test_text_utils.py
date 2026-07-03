"""Tests for recall text extraction."""

from app.services.text_utils import extract_answer_text


def test_extract_from_dict():
    raw = {
        "kind": "graph_completion",
        "text": "The **main** function works via `callback`.",
        "dataset_name": "owner_repo",
    }
    assert extract_answer_text(raw) == "The **main** function works via `callback`."


def test_extract_from_stringified_dict():
    raw = "{'kind': 'graph_completion', 'text': 'Hello\\\\nWorld', 'score': None}"
    assert "Hello" in extract_answer_text(raw)
    assert "World" in extract_answer_text(raw)


def test_extract_from_plain_string():
    assert extract_answer_text("Plain answer") == "Plain answer"
