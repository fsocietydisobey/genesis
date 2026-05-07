"""Tests for the column-name allowlist redactor."""

from chimera.monitor.discovery.redaction import REDACTED_MARKER, redact


def test_top_level_email_redacted():
    state = {"user_email": "alice@example.com", "name": "Alice"}
    out = redact(state)
    assert out["user_email"] == REDACTED_MARKER
    assert out["name"] == "Alice"


def test_password_token_secret_ssn_pii_all_redacted():
    state = {
        "password": "p",
        "auth_token": "t",
        "client_secret": "s",
        "user_ssn": "123",
        "pii_blob": {"any": "thing"},
    }
    out = redact(state)
    for key in state:
        assert out[key] == REDACTED_MARKER, f"expected {key} to be redacted"


def test_case_insensitive_match():
    out = redact({"USER_EMAIL": "x", "Password": "y"})
    assert out["USER_EMAIL"] == REDACTED_MARKER
    assert out["Password"] == REDACTED_MARKER


def test_nested_dicts_redacted():
    state = {"profile": {"contact": {"email": "x", "phone": "555"}}}
    out = redact(state)
    assert out["profile"]["contact"]["email"] == REDACTED_MARKER
    assert out["profile"]["contact"]["phone"] == "555"


def test_lists_of_dicts_redacted():
    state = {"users": [{"email": "a"}, {"email": "b", "name": "B"}]}
    out = redact(state)
    assert out["users"][0]["email"] == REDACTED_MARKER
    assert out["users"][1]["email"] == REDACTED_MARKER
    assert out["users"][1]["name"] == "B"


def test_non_string_keys_pass_through():
    out = redact({1: "one", 2: {"email": "x"}})
    assert out[1] == "one"
    assert out[2]["email"] == REDACTED_MARKER


def test_custom_patterns_replace_defaults():
    out = redact({"email": "x", "custom": "y"}, patterns=("custom",))
    assert out["email"] == "x"
    assert out["custom"] == REDACTED_MARKER


def test_no_match_returns_unchanged_structure():
    state = {"a": 1, "b": [1, 2, {"c": 3}]}
    assert redact(state) == state
