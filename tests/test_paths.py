from pathlib import Path

from utils.paths import data_path

ROOT = Path(__file__).resolve().parent.parent


def test_default_is_repo_root(monkeypatch):
    monkeypatch.delenv("NMA_DATA_DIR", raising=False)
    assert data_path("x.json") == ROOT / "x.json"


def test_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("NMA_DATA_DIR", str(tmp_path))
    assert data_path("x.json") == tmp_path / "x.json"
