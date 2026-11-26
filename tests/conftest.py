import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SNAP_DIR = Path(__file__).resolve().parent / "snapshots"

os.environ.setdefault("DISCORD_TOKEN", "test")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_addoption(parser):
    parser.addoption("--update-snapshots", action="store_true", default=False,
                     help="rewrite golden snapshot files with current output")


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Temp NMA_DATA_DIR containing the real config.json."""
    monkeypatch.setenv("NMA_DATA_DIR", str(tmp_path))
    shutil.copy(ROOT / "config.json", tmp_path / "config.json")
    return tmp_path


def _dump(value):
    return json.dumps(value, sort_keys=True, indent=2, default=str, ensure_ascii=False) + "\n"


@pytest.fixture
def snapshot(request):
    update = request.config.getoption("--update-snapshots")

    def check(name, value):
        path = SNAP_DIR / f"{name}.json"
        text = _dump(value)
        if update or not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            if not update:
                pytest.fail(f"snapshot {name} did not exist; written. Review and re-run.")
            return
        assert text == path.read_text(), f"snapshot {name} differs (use --update-snapshots if intended)"

    return check


def load_bot():
    """Import nma-bot.py (hyphenated filename) as module `nma_bot`."""
    if "nma_bot" in sys.modules:
        return sys.modules["nma_bot"]
    spec = importlib.util.spec_from_file_location("nma_bot", ROOT / "nma-bot.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["nma_bot"] = mod
    spec.loader.exec_module(mod)
    return mod


async def ensure_extensions(bot_module):
    """Load every extension the bot would load in setup_hook (idempotent across tests)."""
    client = bot_module.client
    for name in client.EXTENSIONS:
        if name not in client.extensions:
            await client.load_extension(name)


async def dispatch_message(bot_module, message):
    """Deliver a message to every cog on_message listener (the bot has no prefix commands)."""
    client = bot_module.client
    for listener in list(client.extra_events.get("on_message", [])):
        await listener(message)
