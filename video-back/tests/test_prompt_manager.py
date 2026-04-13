import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from agents.coder import example as coder_example
from prompts.manager import PromptManager


def test_coder_prompt_allows_javascript_object_examples():
    messages = PromptManager().get_langchain_messages("coder", example=coder_example)

    assert messages
    assert "getOrderedMarks" in messages[0].content
    assert "{ minGap: 8" in messages[0].content
