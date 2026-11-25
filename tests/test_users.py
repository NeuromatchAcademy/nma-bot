import json

import discord
import pytest

from tests.fakes import FakeChannel, FakeGuild, FakeMember, FakeMessage, FakeRole, calls_summary
from utils import users

ROLE_NAMES = ["Project TA", "Teaching Assistant", "Lead TA", "Approved User",
              "americas", "europe-africa", "asia-pacific"]
COURSE = "Computational Neuroscience"


def user_entry(role, name="Sam Student", timeslot="4"):
    return {"name": name, "role": role, "timeslot": timeslot, "megapods": ["Alpha"], "pods": ["Blue Rays"]}


class World:
    pass


@pytest.fixture
def world(data_dir):
    w = World()
    w.guild = FakeGuild("CN Test", roles=[FakeRole(n) for n in ROLE_NAMES])
    w.log = w.guild.add_text_channel("bot-log")
    w.general_thread = FakeChannel("General")
    w.pod = w.guild.add_forum("blue-rays", threads=[w.general_thread])
    w.gen = w.guild.add_text_channel("alpha-general")
    w.ta = w.guild.add_text_channel("alpha-ta-chat")
    w.user = FakeMember("sam", 77)
    w.data_dir = data_dir
    w.set_users({"sam@x.org": user_entry("student")})
    (data_dir / "discord-ids.json").write_text("{}")
    return w


def _set_users(self, entries):
    (self.data_dir / "pods.json").write_text(json.dumps(
        {COURSE: {"structure": {"Alpha": ["Blue Rays"]}, "users": entries}}))


World.set_users = _set_users


def msg(w, content="sam@x.org"):
    return FakeMessage(content, author=w.user, channel=w.log, guild=w.guild)


def summary(w):
    return {
        "user": calls_summary(w.user),
        "pod": calls_summary(w.pod),
        "general_thread": calls_summary(w.general_thread),
        "megapod_general": calls_summary(w.gen),
        "megapod_ta": calls_summary(w.ta),
        "bot_log": calls_summary(w.log),
        "nick": w.user.nick,
    }


@pytest.mark.parametrize("role", ["student", "ta", "lead_ta", "project_ta"])
async def test_verify_happy_path(world, snapshot, role, capsys):
    world.set_users({"sam@x.org": user_entry(role)})
    await users.verify_user(msg(world))
    snapshot(f"verify_{role}", summary(world))
    ids = json.loads((world.data_dir / "discord-ids.json").read_text())
    assert ids == {"77": "sam@x.org"}  # int key becomes str on dump
    assert "Verified user sam with email sam@x.org." in capsys.readouterr().out


async def test_student_gets_no_ta_chat_announcement(world):
    await users.verify_user(msg(world))
    assert [c[0] for c in world.ta.calls] == ["set_permissions"]


async def test_non_student_announced_in_ta_chat(world):
    world.set_users({"sam@x.org": user_entry("ta")})
    await users.verify_user(msg(world))
    assert [c[0] for c in world.ta.calls] == ["set_permissions", "send"]


async def test_email_is_lowercased(world):
    await users.verify_user(msg(world, "SAM@X.ORG"))
    assert world.user.nick == "Sam Student"
    assert json.loads((world.data_dir / "discord-ids.json").read_text()) == {"77": "sam@x.org"}


async def test_email_with_whitespace_not_found(world):
    await users.verify_user(msg(world, " sam@x.org"))
    last = calls_summary(world.log)[-1][2]["embed"]
    assert last["title"] == "Failed Verification"
    assert "Reason: User information not found for this course." in last["description"]
    assert world.user.calls == []


async def test_nickname_truncated_to_30(world):
    world.set_users({"sam@x.org": user_entry("student", name="N" * 45)})
    await users.verify_user(msg(world))
    assert world.user.nick == "N" * 30


@pytest.mark.parametrize("slot,role_name", [
    ("1", "asia-pacific"), ("2", "asia-pacific"), ("3", "europe-africa"),
    ("4", "americas"), ("5", "americas")])
async def test_timeslot_role(world, slot, role_name):
    world.set_users({"sam@x.org": user_entry("student", timeslot=slot)})
    await users.verify_user(msg(world))
    assert role_name in [r.name for r in world.user.roles]
    assert len([r for r in world.user.roles if r.name in ("americas", "europe-africa", "asia-pacific")]) == 1


async def test_bad_timeslot_fails_after_partial_side_effects(world):
    world.set_users({"sam@x.org": user_entry("student", timeslot="9")})
    await users.verify_user(msg(world))
    embed = calls_summary(world.log)[-1][2]["embed"]
    assert embed["title"] == "Failed Verification"
    assert "time_role" in embed["description"]  # UnboundLocalError text
    assert "Approved User" in [r.name for r in world.user.roles]  # roles already granted
    assert json.loads((world.data_dir / "discord-ids.json").read_text()) == {}  # never recorded


async def test_missing_pod_channel_reports_failure(world):
    world.guild.channels.remove(world.pod)
    await users.verify_user(msg(world))
    embed = calls_summary(world.log)[-1][2]["embed"]
    assert embed["title"] == "Failed Verification"
    assert "Ran into this issue:" in embed["description"]


async def test_missing_ids_file_raises_before_try(world):
    (world.data_dir / "discord-ids.json").unlink()
    with pytest.raises(FileNotFoundError):
        await users.verify_user(msg(world))


async def test_lookup_user(world):
    (world.data_dir / "discord-ids.json").write_text(json.dumps({"77": "sam@x.org"}))
    info = await users.lookup_user(msg(world), 77)
    assert info["name"] == "Sam Student"
    with pytest.raises(KeyError):
        await users.lookup_user(msg(world), 78)


async def test_mega_from_pod(world):
    assert await users.mega_from_pod(msg(world), "Blue Rays") == "Alpha"
    assert await users.mega_from_pod(msg(world), "Blue-Rays") == "Alpha"  # '-' -> ' '
    assert await users.mega_from_pod(msg(world), "Nope") == "Pod not found"


@pytest.mark.known_bug("lowercased pod names (as MergePods passes them) never match 'Blue Rays'")
async def test_mega_from_pod_lowercase_not_found(world):
    assert await users.mega_from_pod(msg(world), "blue-rays") == "Pod not found"
