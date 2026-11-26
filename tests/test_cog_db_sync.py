import pytest
from discord.ext import commands

from cogs.db_sync import DbSync
from utils import db


@pytest.fixture
def loop_spy(monkeypatch):
    state = {"running": False, "starts": 0, "cancels": 0}

    def start():
        state["running"] = True
        state["starts"] += 1

    def cancel():
        state["running"] = False
        state["cancels"] += 1

    monkeypatch.setattr(db.poll_db, "start", start)
    monkeypatch.setattr(db.poll_db, "cancel", cancel)
    monkeypatch.setattr(db.poll_db, "is_running", lambda: state["running"])
    monkeypatch.setattr(db.poll_db, "_before_loop", None, raising=False)
    return state


class FakeBot:
    def __init__(self):
        self.ready_waits = 0

    async def wait_until_ready(self):
        self.ready_waits += 1


async def test_cog_load_starts_loop_once(loop_spy):
    cog = DbSync(FakeBot())
    await cog.cog_load()
    await cog.cog_load()  # e.g. reload: must not start a second loop
    assert loop_spy["starts"] == 1


async def test_cog_unload_cancels_loop(loop_spy):
    cog = DbSync(FakeBot())
    await cog.cog_load()
    await cog.cog_unload()
    assert loop_spy["cancels"] == 1 and loop_spy["running"] is False


async def test_loop_waits_for_bot_not_a_fixed_sleep(loop_spy):
    bot = FakeBot()
    cog = DbSync(bot)
    await cog.cog_load()
    await db.poll_db._before_loop()
    assert bot.ready_waits == 1


async def test_setup_adds_cog():
    added = []

    class B(commands.Bot):
        async def add_cog(self, cog, **kw):
            added.append(cog)

    from cogs import db_sync
    await db_sync.setup(B(command_prefix="!", intents=__import__("discord").Intents.none()))
    assert isinstance(added[0], DbSync)
