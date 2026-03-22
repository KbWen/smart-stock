"""
Tests for HMAC model signature verification (core/ai/predictor._verify_hmac).

AC1: valid signing key + correct signature → True
AC2: valid signing key + wrong signature → False + warning logged
AC3: MODEL_SIGNING_KEY not configured → True (opt-out, signing disabled)
AC4: .sig sidecar absent → True (legacy model, allow load)
"""
import hashlib
import hmac as _hmac
import logging

import pytest

from core.ai.predictor import _verify_hmac


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sig(key: str, data: bytes) -> str:
    """Compute the expected HMAC-SHA256 hex digest."""
    return _hmac.new(key.encode(), data, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# AC1: Valid key + valid signature → True
# ---------------------------------------------------------------------------

def test_valid_key_and_correct_sig_returns_true(tmp_path, monkeypatch):
    """AC1: Matching HMAC signature must return True."""
    model_path = str(tmp_path / "model.pkl")
    model_bytes = b"fake model binary content"
    signing_key = "test-signing-key-ac1"

    # Write a correct .sig sidecar
    sig = _make_sig(signing_key, model_bytes)
    (tmp_path / "model.pkl.sig").write_text(sig, encoding="utf-8")

    monkeypatch.setattr("core.ai.predictor._cfg.MODEL_SIGNING_KEY", signing_key)
    assert _verify_hmac(model_path, model_bytes) is True


# ---------------------------------------------------------------------------
# AC2: Valid key + wrong signature → False + warning
# ---------------------------------------------------------------------------

def test_wrong_signature_returns_false_and_logs_warning(tmp_path, monkeypatch, caplog):
    """AC2: Signature mismatch → False with a warning log entry."""
    model_path = str(tmp_path / "model.pkl")
    model_bytes = b"legitimate model bytes"
    signing_key = "test-signing-key-ac2"

    # Write a deliberately incorrect .sig sidecar
    (tmp_path / "model.pkl.sig").write_text("deadbeef" * 16, encoding="utf-8")

    monkeypatch.setattr("core.ai.predictor._cfg.MODEL_SIGNING_KEY", signing_key)

    with caplog.at_level(logging.WARNING, logger="core.ai.predictor"):
        result = _verify_hmac(model_path, model_bytes)

    assert result is False
    assert "HMAC signature mismatch" in caplog.text


# ---------------------------------------------------------------------------
# AC3: No signing key configured → True (opt-out)
# ---------------------------------------------------------------------------

def test_no_signing_key_returns_true(tmp_path, monkeypatch):
    """AC3: Empty MODEL_SIGNING_KEY means signing is disabled; always allow load."""
    model_path = str(tmp_path / "model.pkl")
    model_bytes = b"any bytes"

    monkeypatch.setattr("core.ai.predictor._cfg.MODEL_SIGNING_KEY", "")
    assert _verify_hmac(model_path, model_bytes) is True


def test_none_signing_key_returns_true(tmp_path, monkeypatch):
    """AC3 (variant): None MODEL_SIGNING_KEY also disables signing."""
    model_path = str(tmp_path / "model.pkl")
    model_bytes = b"any bytes"

    monkeypatch.setattr("core.ai.predictor._cfg.MODEL_SIGNING_KEY", None)
    assert _verify_hmac(model_path, model_bytes) is True


# ---------------------------------------------------------------------------
# AC4: .sig sidecar absent → True (legacy model, allow load)
# ---------------------------------------------------------------------------

def test_missing_sidecar_returns_true(tmp_path, monkeypatch):
    """AC4: No .sig file present → True (backward-compatible with unsigned models)."""
    model_path = str(tmp_path / "model.pkl")
    model_bytes = b"unsigned legacy model"
    signing_key = "test-signing-key-ac4"

    # Intentionally do NOT create a .sig file
    monkeypatch.setattr("core.ai.predictor._cfg.MODEL_SIGNING_KEY", signing_key)
    assert _verify_hmac(model_path, model_bytes) is True
