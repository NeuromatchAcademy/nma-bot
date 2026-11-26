import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def data_path(name: str) -> Path:
    """Resolve a data file (config.json, pods.json, discord-ids.json).

    Defaults to the repo root; override with the NMA_DATA_DIR env var.
    """
    base = os.getenv("NMA_DATA_DIR")
    return (Path(base) if base else ROOT) / name
