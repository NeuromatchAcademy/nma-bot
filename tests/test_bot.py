import asyncio
import datetime
import json
from types import SimpleNamespace

import discord
import pytest
from discord import app_commands
from discord.ext import commands

from tests.conftest import dispatch_message, ensure_extensions, load_bot
from tests.fakes import (
    FakeChannel,
    FakeDM,
    FakeGuild,
    FakeInteraction,
    FakeMember,
    FakeMessage,
    FakeRole,
    calls_summary,
)
from utils import activities, users

COURSE = "Computational Neuroscience"
ROLE_NAMES = ["Organizers", "Staffers", "Robots", "Lead TA", "Teaching Assistant", "Approved User",
              "americas", "europe-africa", "asia-pacific"]


@pytest.fixture
def bot():
    return load_bot()


class W:
    def member(self, name, id, *roles):
        m = FakeMember(name, id, roles=[discord.utils.get(self.guild.roles, name=r) for r in roles])
        self.guild.members.append(m)
        return m

    async def send(self, content, author=None, channel=None):
        msg = FakeMessage(content, author=author or self.admin, channel=channel or self.chan, guild=self.guild)
        await dispatch_message(self.bot, msg)
        return msg


@pytest.fixture
async def w(bot, data_dir):
    await ensure_extensions(bot)
    w = W()
    w.bot = bot
    w.guild = FakeGuild("CN Test", roles=[FakeRole(r) for r in ROLE_NAMES])
    w.chan = w.guild.add_text_channel("general")
    w.admin = w.member("admin", 1, "Organizers")
    w.plain = w.member("plain", 2)
    (data_dir / "discord-ids.json").write_text("{}")
    w.data_dir = data_dir
    return w


def embeds(chan):
    return [c[2]["embed"] for c in calls_summary(chan) if c[0] == "send" and "embed" in c[2]]


# ------------------------------------------------------------------ on_message routing

async def test_verify_channel_with_email_verifies_then_deletes(w, monkeypatch):
    verify = w.guild.add_text_channel("verify")
    seen = []

    async def fake_verify(m):
        seen.append(m)

    monkeypatch.setattr(users, "verify_user", fake_verify)
    msg = await w.send("me@x.org", author=w.plain, channel=verify)
    assert seen == [msg] and calls_summary(msg) == [["delete", [], {}]]


async def test_verify_channel_without_at_just_deletes(w, monkeypatch):
    verify = w.guild.add_text_channel("verify")

    async def boom(m):
        raise AssertionError("must not verify")

    monkeypatch.setattr(users, "verify_user", boom)
    msg = await w.send("hello", author=w.plain, channel=verify)
    assert calls_summary(msg) == [["delete", [], {}]]


async def test_dm_is_ignored(w):
    dm = FakeDM()
    await w.send("hi", author=w.plain, channel=dm)
    assert dm.calls == []


async def test_plain_chat_and_unknown_command_ignored(w):
    await w.send("hello world")
    await w.send("--nma bogus")
    assert w.chan.calls == []


@pytest.mark.parametrize("text", ["--nma", "--nma identify", "--nma getposts"])
async def test_missing_subcommand_or_argument_is_ignored(w, text):
    await w.send(text)
    assert w.chan.calls == []


async def test_own_messages_ignored(w, bot, monkeypatch):
    me = FakeMember("bot", 99)
    monkeypatch.setattr(bot.client._connection, "user", me, raising=False)
    await w.send("--nma auth", author=me)
    await w.send("--csrun --nma auth", author=me)  # passes the gate but is not a command
    assert w.chan.calls == []
    await w.send("--nma auth", author=w.admin)  # others still work
    assert len(w.chan.calls) == 1


@pytest.mark.parametrize("who,status", [("admin", 1), ("plain", 0)])
async def test_auth(w, who, status):
    await w.send("--nma auth", author=getattr(w, who))
    assert calls_summary(w.chan) == [["send", [f"{who} auth status: {status}."], {}]]


@pytest.mark.parametrize("cmd", ["init", "assign", "unassign", "merge", "swap"])
async def test_removed_commands_are_ignored(w, cmd):
    await w.send(f"--nma {cmd} x")
    assert w.chan.calls == []


@pytest.mark.parametrize("cmd", ["getposts", "timefix"])
async def test_admin_commands_silently_ignored_for_non_admin(w, cmd):
    await w.send(f"--nma {cmd} x", author=w.plain)
    assert w.chan.calls == []


async def test_identify(w):
    chans = {n: w.guild.add_text_channel(n) for n in ("lgbtq", "gender", "race")}
    msg = await w.send("--nma identify lgbtq,race", author=w.plain)
    assert calls_summary(chans["lgbtq"]) == [["set_permissions", ["Member:plain"],
                                              {"view_channel": True, "send_messages": True}]]
    assert calls_summary(chans["race"]) == calls_summary(chans["lgbtq"])
    assert chans["gender"].calls == []
    assert calls_summary(msg) == [["delete", [], {}]]


def podcheck_members(w):
    for name, id, *roles in [("org", 10, "Organizers"), ("bot", 11, "Robots"), ("lead", 12, "Lead TA", "Teaching Assistant"),
                             ("ta", 13, "Teaching Assistant"), ("stu", 14)]:
        w.member(name, id, *roles)
    return [m for m in w.guild.members if m.id >= 10]


async def test_podcheck_forum(w, snapshot):
    forum = w.guild.add_forum("blue-rays")
    forum.overwrites = {m: {} for m in podcheck_members(w)}
    thread = FakeChannel("General", type=discord.ChannelType.public_thread, parent=forum, guild=w.guild)
    await w.send("--nma podcheck", channel=thread)
    snapshot("podcheck_forum", embeds(thread))


async def test_podcheck_megapod_general(w, snapshot):
    general = w.guild.add_text_channel("alpha-general", members=podcheck_members(w))
    thread = FakeChannel("t", type=discord.ChannelType.public_thread, parent=general, guild=w.guild)
    await w.send("--nma podcheck", channel=thread)
    snapshot("podcheck_general", embeds(thread))


async def test_podcheck_other_parent_lists_nobody(w):
    parent = w.guild.add_text_channel("random")
    thread = FakeChannel("t", type=discord.ChannelType.public_thread, parent=parent, guild=w.guild)
    await w.send("--nma podcheck", channel=thread)
    assert embeds(thread)[0]["description"] == "**Current Members:**\n"


def archive_source(w, name="logs"):
    src = w.guild.add_text_channel(name)
    t = datetime.datetime(2030, 1, 2, 3, 4, 5)
    src.history_messages = [
        FakeMessage("two", author=w.plain, channel=src),
        FakeMessage("one", author=w.admin, channel=src),
    ]
    for m in src.history_messages:
        m.created_at = t
    return src


@pytest.mark.parametrize("ref", ["logs", "<#{id}>"])
async def test_getposts(w, ref, tmp_path_factory, monkeypatch):
    cwd = tmp_path_factory.mktemp("cwd")
    monkeypatch.chdir(cwd)
    src = archive_source(w)
    await w.send("--nma getposts " + ref.format(id=src.id))
    assert (cwd / "logs-log.csv").read_text().splitlines() == [
        ",Date,Author,Content", "0,2030-01-02 03:04:05,plain,two", "1,2030-01-02 03:04:05,admin,one"]
    calls = calls_summary(w.chan)
    assert calls[0][2]["embed"]["description"] == "Starting channel archival -- this might take a while!"
    assert calls[1] == ["send", [], {"file": {"file": "logs-log.csv"}}]


async def test_getposts_failure_reports_error(w, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    await w.send("--nma getposts missing")
    err = embeds(w.chan)[1]
    assert err["title"] == "Error!"
    assert err["description"] == "admin, channel archival failed (AttributeError). See the bot logs."
    assert ".py" not in err["description"]  # no file names / line numbers


@pytest.mark.parametrize("slot,expected", [("1", "asia-pacific"), ("2", "asia-pacific"),
                                           ("3", "europe-africa"), ("4", "americas"), ("5", "americas")])
async def test_timefix_roles(w, slot, expected):
    sam = w.member("sam", 50, "Approved User", "europe-africa", "asia-pacific", "americas")
    (w.data_dir / "discord-ids.json").write_text(json.dumps({"50": "sam@x.org"}))
    (w.data_dir / "pods.json").write_text(json.dumps({COURSE: {"structure": {}, "users": {
        "sam@x.org": {"name": "Sam", "timeslot": slot, "role": "student", "pods": [], "megapods": []}}}}))
    await w.send("--nma timefix")
    tz = {"americas", "europe-africa", "asia-pacific"}
    assert {r.name for r in sam.roles} & tz == {expected}
    assert embeds(w.chan)[-1] == {"title": "Time Check", "description": "Checked Sam's time.", "color": 0x00ff2a}


async def test_timefix_unknown_member_reports_and_continues(w):
    w.member("ghost", 60, "Approved User")
    w.member("skipped", 61)  # lacks Approved User -> ignored
    (w.data_dir / "pods.json").write_text(json.dumps({COURSE: {"structure": {}, "users": {}}}))
    await w.send("--nma timefix")
    (e,) = embeds(w.chan)
    assert e["title"] == "Time Check"
    assert e["description"] == "ghost (60) failed: KeyError. See the bot logs."


# ------------------------------------------------------------------ slash command

def cog(bot):
    return bot.client.get_cog("Activities")


def choice(value="Scrabble"):
    return app_commands.Choice(name="x", value=value)


async def start(w, category="alpha", create_cat=True, megapod_games=False):
    cat = w.guild.add_category(category)
    gen = w.guild.add_text_channel(f"{category}-general", cat, members=[
        w.member("org2", 5, "Organizers"), w.member("stu", 6), w.member("bot2", 7, "Robots")])
    here = w.guild.add_text_channel("here", cat)
    games = w.guild.add_voice_channel("megapod-games", cat) if megapod_games else None
    inter = FakeInteraction(user=w.admin, guild=w.guild, channel=here)
    return cat, gen, inter, games


async def test_start_activity_outside_megapod(w, bot):
    _, _, inter, _ = await start(w, category="Social")
    await cog(bot).start_activity.callback(cog(bot), inter, choice())
    assert inter.response.calls == [("send_message", ("You can only use this in megapod channels, admin!",),
                                     {"ephemeral": True})]


async def test_start_activity_creates_games_channel(w, bot, monkeypatch):
    async def fake_invite(game, channel_id):
        return "inv"

    monkeypatch.setattr(activities, "create_activity_invite", fake_invite)
    cat, gen, inter, _ = await start(w)
    await cog(bot).start_activity.callback(cog(bot), inter, choice())
    games = discord.utils.get(w.guild.voice_channels, name="megapod-games")
    assert games.category is cat
    assert calls_summary(games) == [
        ["set_permissions", ["Role:@everyone"], {"view_channel": False}],
        ["set_permissions", ["Member:stu"], {"view_channel": True}]]  # privileged roles skipped
    assert calls_summary(gen) == [["send", ["<@1> has started an activity! Click here to join: https://discord.gg/inv"], {}]]
    assert inter.response.calls[0][1][0].startswith("If this is the first time this command is run")


async def test_start_activity_reuses_games_channel(w, bot, monkeypatch):
    async def fake_invite(game, channel_id):
        return "inv"

    monkeypatch.setattr(activities, "create_activity_invite", fake_invite)
    _, _gen, inter, games = await start(w, megapod_games=True)
    await cog(bot).start_activity.callback(cog(bot), inter, choice())
    assert games.calls == [] and w.guild.calls == []


# ------------------------------------------------------------------ voice / lifecycle

def voice_event(w, cat_name="social", name="Study", members=()):
    cat = w.guild.add_category(cat_name)
    vc = w.guild.add_voice_channel(name, cat, members=list(members))
    return SimpleNamespace(channel=vc), vc


@pytest.mark.parametrize("cat,name,members,scheduled", [
    ("social", "Study", [], True),
    ("social", "Social Voice Chat 1", [], False),
    ("social", "Study", [object()], False),
    ("alpha", "Study", [], False),
])
async def test_voice_state_update_schedules_deletion(w, bot, monkeypatch, cat, name, members, scheduled):
    tasks = []
    monkeypatch.setattr(bot.client, "loop", SimpleNamespace(create_task=lambda c: (tasks.append(c), c.close())), raising=False)
    before, _vc = voice_event(w, cat, name, members)
    await cog(bot).on_voice_state_update(w.plain, before, SimpleNamespace(channel=None))
    assert bool(tasks) is scheduled


async def test_voice_state_update_without_before_channel(w, bot):
    await cog(bot).on_voice_state_update(w.plain, SimpleNamespace(channel=None), SimpleNamespace(channel=None))


async def test_delete_channel_after_deletes_empty(w, bot, monkeypatch):
    slept = []

    async def fake_sleep(s):
        slept.append(s)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    log = w.guild.add_text_channel("bot-log")
    _, vc = voice_event(w)
    await cog(bot).delete_channel_after(vc)
    assert slept == [300]
    assert [e["description"] for e in embeds(log)] == [
        "Voice Channel Study is empty, deleting after 5 minutes...", "Deleting channel Study"]
    assert calls_summary(vc) == [["delete", [], {"reason": "Inactive for 5 Minutes"}]]


async def test_delete_channel_after_skips_when_repopulated(w, bot, monkeypatch):
    async def fake_sleep(s):
        vc.members.append(w.plain)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    log = w.guild.add_text_channel("bot-log")
    _, vc = voice_event(w)
    await cog(bot).delete_channel_after(vc)
    assert vc.calls == [] and len(embeds(log)) == 1


async def test_delete_channel_after_user_deleted(w, bot, monkeypatch, capsys):
    async def fake_sleep(s):
        w.guild.channels.remove(vc)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    w.guild.add_text_channel("bot-log")
    _, vc = voice_event(w)
    await cog(bot).delete_channel_after(vc)
    assert vc.calls == [] and "User deleted channel Study" in capsys.readouterr().out


async def test_on_ready(w, bot, monkeypatch, snapshot, capsys):
    synced = []

    async def fake_sync():
        synced.append(1)

    monkeypatch.setattr(bot.tree, "sync", fake_sync)
    monkeypatch.setattr(type(bot.client), "guilds", property(lambda self: [w.guild]))
    monkeypatch.setattr(bot.client._connection, "user", SimpleNamespace(name="nmabot", id=5), raising=False)
    chans = {n: w.guild.add_text_channel(n) for n in ("command-center", "verify", "activity-center", "bot-log")}
    for n in ("command-center", "verify", "activity-center"):
        chans[n].history_messages = [FakeMessage("old1"), FakeMessage("old2")]
    await bot.client.on_ready()
    assert synced == [1]
    snapshot("on_ready", {n: calls_summary(c) for n, c in chans.items()})
    for n in ("command-center", "verify", "activity-center"):
        assert [calls_summary(m) for m in chans[n].history_messages] == [[["delete", [], {}]]] * 2
        assert calls_summary(chans[n].sent[0]) == [["pin", [], {}]]
    assert chans["bot-log"].sent[0].calls == []  # restart notice is not pinned
    assert "Logged in as\nnmabot\n5" in capsys.readouterr().out


def test_bot_is_commands_bot_with_presence(bot):
    assert isinstance(bot.client, commands.Bot)
    assert bot.client.tree is bot.tree
    assert bot.client.activity.name == "Studying brains..."
    assert bot.client.activity.type == discord.ActivityType.watching


async def test_setup_hook_loads_extensions(bot, monkeypatch):
    loaded = []

    async def fake_load(name):
        loaded.append(name)

    monkeypatch.setattr(bot.client, "load_extension", fake_load)
    monkeypatch.setattr(type(bot.client), "EXTENSIONS", ("cogs.a", "cogs.b"))
    await bot.client.setup_hook()
    assert loaded == ["cogs.a", "cogs.b"]


async def test_verify_channel_never_runs_commands(w, monkeypatch):
    verify = w.guild.add_text_channel("verify")

    async def fake_verify(m):
        pass

    monkeypatch.setattr(users, "verify_user", fake_verify)
    msg = await w.send("--nma auth me@x.org", author=w.admin, channel=verify)
    assert calls_summary(msg) == [["delete", [], {}]]
    assert verify.calls == []  # no "auth status" reply


async def test_bot_own_message_not_verified(w, bot, monkeypatch):
    verify = w.guild.add_text_channel("verify")
    me = FakeMember("bot", 99)
    monkeypatch.setattr(bot.client._connection, "user", me, raising=False)
    msg = await w.send("me@x.org", author=me, channel=verify)
    assert msg.calls == []


def test_start_activity_registered_on_tree(w, bot):
    assert bot.tree.get_command("start_activity") is not None


async def test_default_extensions(bot):
    assert bot.NmaBot.EXTENSIONS == ("cogs.verify", "cogs.admin_tools", "cogs.activities", "cogs.db_sync")
