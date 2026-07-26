"""Regression guards for the Tier 1 repo hygiene contract.

These pin decisions that are easy to silently undo with a stray `git add`:

* runtime artifacts (`stock_list_cache.json`, `tw_stocks_analysis_refined.csv`)
  are produced by `core/config.py` / `fetch_stocks.py` at runtime and must stay
  out of version control — a committed cache goes stale and gets served as if
  it were current;
* `deploy_brain.*` installer wrappers live under `installers/` only. The old
  root copies lacked the cache-origin verification in
  `installers/deploy_brain.sh`, so re-adding them would reintroduce a path that
  pulls and execs a framework source without checking where it came from;
* archived Work Log filenames must end in `.md`, or every `*.md` validator
  silently skips them (this is how two files accumulated years of unnoticed
  content defects).

No network and no Docker needed — these read the repo and ask git what it tracks.
"""
import os
import shutil
import subprocess

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RUNTIME_ARTIFACTS = ("stock_list_cache.json", "tw_stocks_analysis_refined.csv")
WRAPPERS = ("deploy_brain.sh", "deploy_brain.ps1", "deploy_brain.cmd")


def _git(*args):
    """Run a git command in the repo, or skip if git/the repo is unavailable."""
    if shutil.which("git") is None:
        pytest.skip("git not available")
    proc = subprocess.run(
        ("git", *args), cwd=_ROOT, capture_output=True, text=True
    )
    if proc.returncode != 0:
        pytest.skip(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def _read(name):
    with open(os.path.join(_ROOT, name), encoding="utf-8") as f:
        return f.read()


def test_runtime_artifacts_are_not_tracked():
    tracked = set(_git("ls-files").splitlines())
    for artifact in RUNTIME_ARTIFACTS:
        assert artifact not in tracked, (
            f"{artifact} is a runtime artifact and must not be committed — "
            "a committed copy goes stale and is served as if current"
        )


def test_runtime_artifacts_are_gitignored():
    ignored = _read(".gitignore").splitlines()
    for artifact in RUNTIME_ARTIFACTS:
        assert artifact in ignored, f"{artifact} must be listed in .gitignore"


def test_installer_wrappers_live_only_under_installers():
    for wrapper in WRAPPERS:
        assert not os.path.exists(os.path.join(_ROOT, wrapper)), (
            f"{wrapper} must not exist at the repo root — the root copy skipped "
            "the cache-origin check that installers/deploy_brain.sh performs"
        )
        assert os.path.exists(os.path.join(_ROOT, "installers", wrapper)), (
            f"installers/{wrapper} is the canonical wrapper and must exist"
        )


def test_manifest_records_only_the_installers_wrappers():
    manifest = _read(".agentcortex-manifest")
    for wrapper in WRAPPERS:
        assert f"installers/{wrapper}" in manifest
        assert f"\nwrapper {wrapper}" not in manifest, (
            f"manifest must not record a root-level {wrapper}"
        )


def test_archived_worklog_filenames_end_in_md():
    archive = os.path.join(_ROOT, ".agentcortex", "context", "archive")
    for entry in os.listdir(archive):
        path = os.path.join(archive, entry)
        if os.path.isdir(path) or entry.startswith("."):
            continue
        assert entry.endswith((".md", ".jsonl")), (
            f"archived file {entry!r} has a malformed name — every *.md "
            "validator silently skips files that do not end in .md"
        )
