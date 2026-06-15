"""Prompt registry loads the active versioned files."""
import prompts


def test_system_persona_loads():
    text = prompts.get_prompt("system_persona")
    assert "Fluidra Pool Assistant" in text
    assert "provided context" in text.lower()
    assert "grounding rules" in text.lower()


def test_active_file_is_versioned():
    assert prompts.active_file("system_persona") == "system_persona.v1.md"


def test_unknown_prompt_raises():
    import pytest

    with pytest.raises(KeyError):
        prompts.get_prompt("does_not_exist")
