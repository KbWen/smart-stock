"""Regression guard for the Docker self-seed contract (v1 #6).

Docker itself is not built here (no daemon in CI/dev); these tests assert the
image WILL produce a populated dashboard: it bundles the demo fixture + seed
script and seeds before serving, and .dockerignore keeps the demo while
excluding the dev DB + models. The offline seed itself is covered by
tests/test_scripts_seed_demo.py.
"""
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(name):
    with open(os.path.join(_ROOT, name), encoding="utf-8") as f:
        return f.read()


def test_dockerfile_copies_seed_script_and_demo_fixture():
    df = _read("Dockerfile")
    assert "COPY scripts/" in df, "image must bundle scripts/ (seed_demo.py)"
    assert "COPY data/demo/" in df, "image must bundle the offline demo fixture"


def test_dockerfile_uses_seed_then_serve_entrypoint():
    df = _read("Dockerfile")
    # a real, non-commented ENTRYPOINT line that runs the seed-then-serve script
    assert any(
        line.strip().startswith("ENTRYPOINT") and "docker-entrypoint.sh" in line
        for line in df.splitlines()
    ), "Dockerfile must use the seed-then-serve ENTRYPOINT"


def test_entrypoint_seeds_before_serving_and_execs():
    ep = _read("docker-entrypoint.sh")
    seed_i = ep.find("seed_demo.py")
    serve_i = ep.find("backend/main.py")
    assert seed_i != -1 and serve_i != -1
    assert seed_i < serve_i, "must seed BEFORE serving"
    assert "exec python backend/main.py" in ep, "exec so the server gets stop signals"


def test_dockerignore_excludes_local_db_and_models_but_keeps_demo():
    di = _read(".dockerignore")
    lines = {line.strip() for line in di.splitlines()}
    # the dev DB lives at the repo ROOT (config.py DB_PATH = BASE_DIR/storage.db),
    # so a root-anchored exclude is required — `data/storage.db` alone is NOT enough.
    assert "storage.db" in lines, "root dev storage.db must be excluded (never baked)"
    assert "*.pkl" in lines, "models must be excluded (honesty — AI stays N/A in-container)"
    assert "node_modules" in di
    assert not (lines & {"data", "data/", "data/demo", "data/demo/"}), \
        "the demo fixture must remain copyable into the image"
