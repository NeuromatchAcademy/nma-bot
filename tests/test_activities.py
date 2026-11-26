import datetime

import discord
import pytest

from tests.fakes import FakeEvent, FakeGuild, FakeInteraction, FakeMember, calls_summary
from utils import activities
from utils.constants import activity_index


class FakeResp:
    def __init__(self, status, body):
        self.status, self._body = status, body

    async def json(self):
        return self._body


class _Ctx:
    def __init__(self, v):
        self.v = v

    async def __aenter__(self):
        return self.v

    async def __aexit__(self, *a):
        return False


def patch_http(monkeypatch, status, body):
    seen = {}

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        def post(self, url, headers=None, json=None):
            seen.update(url=url, headers=headers, json=json)
            return _Ctx(FakeResp(status, body))

    monkeypatch.setattr(activities.aiohttp, "ClientSession", Session)
    return seen


async def test_invite_success(monkeypatch, capsys):
    seen = patch_http(monkeypatch, 200, {"code": "abc"})
    assert await activities.create_activity_invite("Poker Night", 42) == "abc"
    assert seen["url"] == "https://discord.com/api/v9/channels/42/invites"
    assert seen["json"] == {"max_age": 0, "target_type": 2,
                            "target_application_id": activity_index["Poker Night"]["id"]}
    assert seen["headers"] == {"authorization": f"Bot {activities.discordToken}",
                               "content-type": "application/json"}
    assert "Invite created: https://discord.gg/abc" in capsys.readouterr().out


async def test_invite_failure_returns_none(monkeypatch, capsys):
    patch_http(monkeypatch, 403, {"message": "nope"})
    assert await activities.create_activity_invite("Poker Night", 42) is None
    assert "Error: {'message': 'nope'}" in capsys.readouterr().out


async def test_invite_unknown_activity():
    with pytest.raises(KeyError):
        await activities.create_activity_invite("Nope", 1)


def setup_social():
    guild = FakeGuild("g")
    cat = guild.add_category("social")
    inter = FakeInteraction(user=FakeMember("u", 1), guild=guild)
    return guild, cat, inter


@pytest.mark.parametrize("title,count,expected", [
    ("", 0, "Chess In The Park"),
    ("study", 0, "study"),
    ("", 2, "Chess In The Park-2"),
    ("study", 2, "study-2"),
])
async def test_channel_naming_creates_in_social(title, count, expected):
    guild, cat, inter = setup_social()
    ch = await activities.get_activity_channel(inter, "Chess In The Park", title, count)
    assert ch.name == expected and ch.category is cat
    assert calls_summary(guild) == [["create_voice_channel", [expected], {"category": "Category:social"}]]


async def test_channel_reused_when_room():
    guild, cat, inter = setup_social()
    existing = guild.add_voice_channel("Scrabble", cat, members=[1, 2])  # max 8
    assert await activities.get_activity_channel(inter, "Scrabble") is existing
    assert guild.calls == []


async def test_channel_reused_when_unlimited():
    guild, cat, inter = setup_social()
    existing = guild.add_voice_channel("Chess In The Park", cat, members=list(range(50)))  # max 0
    assert await activities.get_activity_channel(inter, "Chess In The Park") is existing


async def test_channel_expands_when_full():
    guild, cat, inter = setup_social()
    guild.add_voice_channel("Putt Party", cat, members=[1])          # max 1 -> full
    guild.add_voice_channel("Putt Party-1", cat, members=[1])        # full too
    ch = await activities.get_activity_channel(inter, "Putt Party")
    assert ch.name == "Putt Party-2"


async def test_channel_unknown_activity_when_existing():
    guild, cat, inter = setup_social()
    guild.add_voice_channel("Nope", cat)
    with pytest.raises(KeyError):
        await activities.get_activity_channel(inter, "Nope")


async def test_event_created_when_none(monkeypatch):
    now = datetime.datetime(2030, 1, 1, tzinfo=datetime.UTC)
    monkeypatch.setattr(discord.utils, "utcnow", lambda: now)
    guild, cat, inter = setup_social()
    vc = guild.add_voice_channel("v", cat)
    ev = await activities.get_activity_event(inter, "Study Session", vc)
    kw = guild.calls[0][2]
    assert kw == {"name": "Study Session", "start_time": now + datetime.timedelta(seconds=60),
                  "entity_type": discord.EntityType.voice, "channel": vc,
                  "privacy_level": discord.PrivacyLevel.guild_only, "reason": "u started Study Session."}
    assert ev is guild.scheduled_events[0]


async def test_event_created_when_name_missing():
    guild, cat, inter = setup_social()
    guild.scheduled_events.append(FakeEvent("Other"))
    ev = await activities.get_activity_event(inter, "Hang Out", guild.add_voice_channel("v", cat))
    assert ev.name == "Hang Out" and len(guild.scheduled_events) == 2


async def test_event_reused_when_exists():
    guild, _cat, inter = setup_social()
    existing = FakeEvent("Hang Out")
    guild.scheduled_events.append(existing)
    assert await activities.get_activity_event(inter, "Hang Out", None) is existing
    assert guild.calls == []
