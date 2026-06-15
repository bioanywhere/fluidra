"""
prompts — versioned prompt templates + system personas.

Prompts are files, not string literals in code, so a change is a reviewable,
revertible diff that runs through evals (blueprint §6.3). `get_prompt(name)`
resolves a logical name through registry.yaml to its active versioned file.
"""
from pathlib import Path

import yaml

_DIR = Path(__file__).parent
_REGISTRY: dict[str, str] = yaml.safe_load((_DIR / "registry.yaml").read_text(encoding="utf-8"))

VERSION = "2025.06.0"


def get_prompt(name: str) -> str:
    """Return the text of the active version of a named prompt."""
    if name not in _REGISTRY:
        raise KeyError(f"unknown prompt {name!r}; known: {sorted(_REGISTRY)}")
    return (_DIR / _REGISTRY[name]).read_text(encoding="utf-8")


def active_file(name: str) -> str:
    """Return the active filename for a prompt (e.g. 'system_persona.v1.md')."""
    return _REGISTRY[name]


__all__ = ["get_prompt", "active_file", "VERSION"]
