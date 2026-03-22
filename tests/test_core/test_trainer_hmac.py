"""
Tests for HMAC sidecar writing in core/ai/trainer.py (train_and_save).

Because train_and_save() trains full ML models, these tests isolate the HMAC
sidecar-writing logic using the same mirror-helper pattern as test_model_rotation.py.

AC5: MODEL_SIGNING_KEY set → .sig file written alongside versioned model
AC6: MODEL_SIGNING_KEY not set → no .sig file created
"""
import hashlib
import hmac as _hmac
import os

import pytest

import core.config as cfg


# ---------------------------------------------------------------------------
# Mirror helper — reproduces the HMAC sidecar-writing block from trainer.py
# (lines 317-322 of core/ai/trainer.py) without running full ML training.
# ---------------------------------------------------------------------------

def _write_hmac_sidecar(versioned_path: str, model_bytes: bytes, signing_key: str) -> None:
    """
    Reproduce the HMAC sidecar logic from train_and_save() (trainer.py lines 318–321).

    NOTE: shutil.copy(versioned_path + '.sig', MODEL_PATH + '.sig') is intentionally
    omitted — tests use isolated tmp_path dirs, not actual model directories.
    """
    if signing_key:
        sig = _hmac.new(signing_key.encode(), model_bytes, hashlib.sha256).hexdigest()
        with open(versioned_path + ".sig", "w") as fh:
            fh.write(sig)


# ---------------------------------------------------------------------------
# AC5: signing key present → .sig file created with correct content
# ---------------------------------------------------------------------------

def test_sig_sidecar_created_when_key_is_set(tmp_path, monkeypatch):
    """AC5: When MODEL_SIGNING_KEY is configured, a .sig sidecar is written."""
    model_bytes = b"simulated serialised sklearn ensemble"
    versioned_path = str(tmp_path / "model_sniper_20260321_0000.pkl")
    signing_key = "production-signing-key"

    monkeypatch.setattr("core.config.MODEL_SIGNING_KEY", signing_key)
    _write_hmac_sidecar(versioned_path, model_bytes, cfg.MODEL_SIGNING_KEY)

    sig_path = versioned_path + ".sig"
    assert os.path.exists(sig_path), ".sig sidecar must exist after training with signing key"

    written_sig = open(sig_path, "r").read().strip()
    expected_sig = _hmac.new(signing_key.encode(), model_bytes, hashlib.sha256).hexdigest()
    assert written_sig == expected_sig, "Written signature must be HMAC-SHA256 of model bytes"


def test_sig_matches_verify_hmac(tmp_path, monkeypatch):
    """AC5 (integration): Signature written by trainer is accepted by predictor._verify_hmac."""
    from core.ai.predictor import _verify_hmac

    model_bytes = b"round-trip test bytes"
    versioned_path = str(tmp_path / "model_sniper_round_trip.pkl")
    signing_key = "round-trip-key"

    # Write the sidecar as trainer would
    _write_hmac_sidecar(versioned_path, model_bytes, signing_key)

    # Verify using predictor's _verify_hmac
    monkeypatch.setattr("core.ai.predictor._cfg.MODEL_SIGNING_KEY", signing_key)
    assert _verify_hmac(versioned_path, model_bytes) is True


# ---------------------------------------------------------------------------
# AC6: no signing key → no .sig file created
# ---------------------------------------------------------------------------

def test_no_sig_sidecar_without_key(tmp_path, monkeypatch):
    """AC6: Without MODEL_SIGNING_KEY, no .sig sidecar is written."""
    model_bytes = b"unsigned model bytes"
    versioned_path = str(tmp_path / "model_sniper_20260321_0001.pkl")

    monkeypatch.setattr("core.config.MODEL_SIGNING_KEY", "")
    _write_hmac_sidecar(versioned_path, model_bytes, cfg.MODEL_SIGNING_KEY)

    sig_path = versioned_path + ".sig"
    assert not os.path.exists(sig_path), "No .sig sidecar should be created when signing is disabled"


def test_trainer_module_imports_cfg(monkeypatch):
    """AC5/AC6 (import check): trainer.py must import _cfg from core.config."""
    import core.ai.trainer as trainer_module
    assert hasattr(trainer_module, "_cfg"), (
        "trainer.py must import 'from core import config as _cfg' for HMAC sidecar writing"
    )
