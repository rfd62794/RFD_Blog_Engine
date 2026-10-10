"""
tests/test_model_router.py

Free-lane guarantees: OpenRouter fallback entries in role_models must be
free-tier slugs (model id ending ":free"). groq/gemini/ollama have no :free
requirement — they are free by construction in this repo's usage.
"""

import pytest

from blog_engine.infra.model_router import role_models


@pytest.mark.parametrize("role", ["generation", "default"])
def test_openrouter_entries_are_free_tier(role):
    """Every openrouter model id in role_models[role] must end in ':free'."""
    openrouter_ids = [m for p, m in role_models[role] if p == "openrouter"]
    assert openrouter_ids, f"role {role!r} has no openrouter fallback entry"
    for model_id in openrouter_ids:
        assert model_id.endswith(":free"), (
            f"role {role!r} openrouter model {model_id!r} is not a free-tier slug"
        )


def test_generation_role_no_paid_claude():
    """Regression: the paid anthropic/claude-3-haiku leak must not return."""
    generation_ids = [m for _, m in role_models["generation"]]
    assert "anthropic/claude-3-haiku" not in generation_ids
