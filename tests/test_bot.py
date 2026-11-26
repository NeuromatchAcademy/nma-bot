import asyncio
import datetime
import json
import logging
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


# ------------------------------------------------------------------ verify channel routing

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


# ------------------------------------------------------------------ admin slash commands

def admin_cog(bot):
    return bot.client.get_cog("AdminTools")


def members_cog(bot):
    return bot.client.get_cog("Members")


def run(bot, name, inter, **kw):
    cog_ = members_cog(bot) if name in ("identify", "podcheck") else admin_cog(bot)
    return getattr(cog_, name).callback(cog_, inter, **kw)


def inter_for(w, user=None, channel=None):
    return FakeInteraction(user=user or w.admin, guild=w.guild, channel=channel or w.chan)


def reply_embed(inter):
    e = inter.response.calls[0][2]["embed"]
    return {"title": e.title, "description": e.description, "color": e.colour.value}


def followup_embeds(inter):
    return [kw["embed"] for _n, _a, kw in inter.followup.calls if "embed" in kw]


def test_text_commands_are_gone(bot):
    assert not hasattr(admin_cog(bot), "on_message") and not hasattr(members_cog(bot), "on_message")
    names = {c.name for c in bot.tree.get_commands()}
    assert {"identify", "podcheck", "getposts", "timefix", "start_activity"} <= names
    assert "auth" not in names


@pytest.mark.parametrize("name", ["getposts", "timefix"])
def test_admin_commands_are_hidden_from_non_administrators(bot, name):
    cmd = bot.tree.get_command(name)
    assert cmd.default_permissions.administrator is True
    assert cmd.guild_only is True


@pytest.mark.parametrize("name,kw", [("getposts", {"channel": None}), ("timefix", {})])
async def test_admin_commands_deny_non_admins(w, bot, monkeypatch, name, kw):
    monkeypatch.delenv("ADMIN_USER_IDS", raising=False)
    inter = inter_for(w, user=w.plain)
    await run(bot, name, inter, **kw)
    (call_name, _args, kwargs), = inter.response.calls
    assert call_name == "send_message" and kwargs["ephemeral"] is True
    assert kwargs["embed"].title == "Administrative Notice"
    assert inter.followup.calls == []


async def test_identify(w, bot):
    chans = {n: w.guild.add_text_channel(n) for n in ("lgbtq", "gender", "race")}
    inter = inter_for(w, user=w.plain)
    await run(bot, "identify", inter, lgbtq=True, gender=False, race=True)
    assert calls_summary(chans["lgbtq"]) == [["set_permissions", ["Member:plain"],
                                              {"view_channel": True, "send_messages": True}]]
    assert calls_summary(chans["race"]) == calls_summary(chans["lgbtq"])
    assert chans["gender"].calls == []
    assert inter.response.calls == [("send_message", ("Access granted: lgbtq, race.",), {"ephemeral": True})]


async def test_identify_requires_a_choice(w, bot):
    inter = inter_for(w, user=w.plain)
    await run(bot, "identify", inter)
    assert inter.response.calls == [("send_message", ("Choose at least one channel.",), {"ephemeral": True})]


async def test_identify_reports_missing_channels(w, bot):
    w.guild.add_text_channel("race")
    inter = inter_for(w, user=w.plain)
    await run(bot, "identify", inter, gender=True, race=True)
    assert inter.response.calls[0][1][0] == (
        "Access granted: race. Not available on this server: gender.")


def podcheck_members(w):
    for name, id, *roles in [("org", 10, "Organizers"), ("bot", 11, "Robots"), ("lead", 12, "Lead TA", "Teaching Assistant"),
                             ("ta", 13, "Teaching Assistant"), ("stu", 14)]:
        w.member(name, id, *roles)
    return [m for m in w.guild.members if m.id >= 10]


async def test_podcheck_forum(w, bot, snapshot):
    forum = w.guild.add_forum("blue-rays")
    forum.overwrites = {m: {} for m in podcheck_members(w)}
    thread = FakeChannel("General", type=discord.ChannelType.public_thread, parent=forum, guild=w.guild)
    inter = inter_for(w, channel=thread)
    await run(bot, "podcheck", inter)
    snapshot("podcheck_forum", [reply_embed(inter)])


async def test_podcheck_megapod_general(w, bot, snapshot):
    general = w.guild.add_text_channel("alpha-general", members=podcheck_members(w))
    thread = FakeChannel("t", type=discord.ChannelType.public_thread, parent=general, guild=w.guild)
    inter = inter_for(w, channel=thread)
    await run(bot, "podcheck", inter)
    snapshot("podcheck_general", [reply_embed(inter)])


async def test_podcheck_other_parent_lists_nobody(w, bot):
    parent = w.guild.add_text_channel("random")
    thread = FakeChannel("t", type=discord.ChannelType.public_thread, parent=parent, guild=w.guild)
    inter = inter_for(w, channel=thread)
    await run(bot, "podcheck", inter)
    assert reply_embed(inter)["description"] == "**Current Members:**\n"


async def test_podcheck_works_in_a_plain_channel(w, bot):
    general = w.guild.add_text_channel("alpha-general", members=podcheck_members(w))
    inter = inter_for(w, channel=general)
    await run(bot, "podcheck", inter)
    assert "lead **(Lead TA)**" in reply_embed(inter)["description"]


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


async def test_getposts(w, bot, tmp_path_factory, monkeypatch):
    cwd = tmp_path_factory.mktemp("cwd")
    monkeypatch.chdir(cwd)
    inter = inter_for(w)
    await run(bot, "getposts", inter, channel=archive_source(w))
    assert inter.response.calls == [("defer", (), {"ephemeral": True, "thinking": True})]
    (_name, _args, kw), = inter.followup.calls
    assert kw["ephemeral"] is True and kw["file"].filename == "logs-log.csv"
    assert kw["file"].fp.read().decode().splitlines() == [
        "Date,Author,Content", "2030-01-02 03:04:05,plain,two", "2030-01-02 03:04:05,admin,one"]
    assert list(cwd.iterdir()) == []  # nothing left behind in the working directory


async def test_getposts_failure_reports_error(w, bot):
    class Broken:
        name = "broken"

        def history(self, limit=None):
            raise RuntimeError("secret internals")

    inter = inter_for(w)
    await run(bot, "getposts", inter, channel=Broken())
    (err,) = followup_embeds(inter)
    assert err.title == "Error!"
    assert err.description == "admin, channel archival failed (RuntimeError). See the bot logs."
    assert "secret" not in err.description


def timefix_world(w, slot):
    sam = w.member("sam", 50, "Approved User", "europe-africa", "asia-pacific", "americas")
    (w.data_dir / "discord-ids.json").write_text(json.dumps({"50": "sam@x.org"}))
    (w.data_dir / "pods.json").write_text(json.dumps({COURSE: {"structure": {}, "users": {
        "sam@x.org": {"name": "Sam", "timeslot": slot, "role": "student", "pods": [], "megapods": []}}}}))
    return sam


@pytest.mark.parametrize("slot,expected", [("1", "asia-pacific"), ("2", "asia-pacific"),
                                           ("3", "europe-africa"), ("4", "americas"), ("5", "americas")])
async def test_timefix_roles(w, bot, slot, expected):
    sam = timefix_world(w, slot)
    inter = inter_for(w)
    await run(bot, "timefix", inter)
    tz = {"americas", "europe-africa", "asia-pacific"}
    assert {r.name for r in sam.roles} & tz == {expected}
    (summary,) = followup_embeds(inter)
    assert summary.title == "Time Check"
    assert summary.description == "Checked the time zone of 1 member(s)."


async def test_timefix_unknown_member_reports_and_continues(w, bot):
    w.member("ghost", 60, "Approved User")
    w.member("skipped", 61)  # lacks Approved User -> ignored
    (w.data_dir / "pods.json").write_text(json.dumps({COURSE: {"structure": {}, "users": {}}}))
    inter = inter_for(w)
    await run(bot, "timefix", inter)
    (summary,) = followup_embeds(inter)
    assert summary.description.splitlines() == [
        "Checked the time zone of 0 member(s).",
        "ghost (60) failed: KeyError. See the bot logs."]


async def test_timefix_caps_reported_failures(w, bot):
    for i in range(25):
        w.member(f"ghost{i}", 100 + i, "Approved User")
    (w.data_dir / "pods.json").write_text(json.dumps({COURSE: {"structure": {}, "users": {}}}))
    inter = inter_for(w)
    await run(bot, "timefix", inter)
    lines = followup_embeds(inter)[0].description.splitlines()
    assert len(lines) == 1 + 20 + 1 and lines[-1] == "...and 5 more failure(s)."


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


async def test_start_activity_without_category(w, bot):
    inter = FakeInteraction(user=w.admin, guild=w.guild, channel=w.guild.add_text_channel("loose", None))
    await cog(bot).start_activity.callback(cog(bot), inter, choice())
    assert inter.response.calls[0][1][0].startswith("You can only use this in megapod channels")


async def test_start_activity_missing_general_channel(w, bot):
    cat = w.guild.add_category("alpha")
    here = w.guild.add_text_channel("here", cat)
    inter = FakeInteraction(user=w.admin, guild=w.guild, channel=here)
    await cog(bot).start_activity.callback(cog(bot), inter, choice())
    assert "alpha-general" in inter.response.calls[0][1][0]


async def test_start_activity_invite_failure_posts_nothing(w, bot, monkeypatch):
    async def failing_invite(game, channel_id):
        raise activities.InviteError("HTTP 403")

    monkeypatch.setattr(activities, "create_activity_invite", failing_invite)
    _cat, gen, inter, _ = await start(w)
    await cog(bot).start_activity.callback(cog(bot), inter, choice())
    assert gen.calls == []
    assert "would not create" in inter.followup.calls[0][1][0]


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
    def create_task(coro):
        tasks.append(coro)
        coro.close()
        return SimpleNamespace(add_done_callback=lambda cb: None, cancel=lambda: None)

    monkeypatch.setattr(bot.client, "loop", SimpleNamespace(create_task=create_task), raising=False)
    before, _vc = voice_event(w, cat, name, members)
    await cog(bot).on_voice_state_update(w.plain, before, SimpleNamespace(channel=None))
    assert bool(tasks) is scheduled


async def test_voice_state_update_dedupes_pending_deletions(w, bot, monkeypatch):
    tasks = []

    def create_task(coro):
        tasks.append(coro)
        coro.close()
        return SimpleNamespace(add_done_callback=lambda cb: None, cancel=lambda: None)

    monkeypatch.setattr(bot.client, "loop", SimpleNamespace(create_task=create_task), raising=False)
    before, _vc = voice_event(w)
    for _ in range(3):
        await cog(bot).on_voice_state_update(w.plain, before, SimpleNamespace(channel=None))
    assert len(tasks) == 1


async def test_voice_state_update_channel_without_category(w, bot):
    vc = w.guild.add_voice_channel("loose", None)
    await cog(bot).on_voice_state_update(w.plain, SimpleNamespace(channel=vc), SimpleNamespace(channel=None))


async def test_delete_channel_after_tolerates_missing_log_channel_and_already_deleted(w, bot, monkeypatch):
    async def fake_sleep(s):
        pass

    async def gone(**kw):
        raise discord.NotFound(SimpleNamespace(status=404, reason="x"), "gone")

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    _, vc = voice_event(w)
    monkeypatch.setattr(vc, "delete", gone)
    await cog(bot).delete_channel_after(vc)  # no bot-log channel, delete raises NotFound


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


async def test_delete_channel_after_user_deleted(w, bot, monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    async def fake_sleep(s):
        w.guild.channels.remove(vc)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    w.guild.add_text_channel("bot-log")
    _, vc = voice_event(w)
    await cog(bot).delete_channel_after(vc)
    assert vc.calls == [] and "User deleted channel Study" in caplog.text


async def test_on_ready(w, bot, monkeypatch, snapshot, caplog):
    caplog.set_level("INFO")
    monkeypatch.setattr(type(bot.client), "guilds", property(lambda self: [w.guild]))
    monkeypatch.setattr(bot.client._connection, "user", SimpleNamespace(name="nmabot", id=5), raising=False)
    chans = {n: w.guild.add_text_channel(n) for n in ("command-center", "verify", "activity-center", "bot-log")}
    for n in ("command-center", "verify", "activity-center"):
        chans[n].history_messages = [FakeMessage("old1"), FakeMessage("old2")]
    ready = bot.client.get_cog("CommandCenter")
    ready._ready_once = False
    await ready.on_ready()
    snapshot("on_ready", {n: calls_summary(c) for n, c in chans.items()})
    for n in ("command-center", "verify", "activity-center"):
        assert [calls_summary(m) for m in chans[n].history_messages] == [[["delete", [], {}]]] * 2
        assert calls_summary(chans[n].sent[0]) == [["pin", [], {}]]
    assert chans["bot-log"].sent[0].calls == []  # restart notice is not pinned
    assert "Logged in as nmabot (5)" in caplog.text


def test_bot_is_commands_bot_with_presence(bot):
    assert isinstance(bot.client, commands.Bot)
    assert bot.client.tree is bot.tree
    assert bot.client.activity.name == "Studying brains..."
    assert bot.client.activity.type == discord.ActivityType.watching


async def test_setup_hook_loads_extensions(bot, monkeypatch):
    loaded = []

    async def fake_load(name):
        loaded.append(name)

    async def fake_sync():
        loaded.append("sync")

    monkeypatch.setattr(bot.client, "load_extension", fake_load)
    monkeypatch.setattr(bot.tree, "sync", fake_sync)
    monkeypatch.setattr(type(bot.client), "EXTENSIONS", ("cogs.a", "cogs.b"))
    await bot.client.setup_hook()
    assert loaded == ["cogs.a", "cogs.b", "sync"]


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
    assert bot.NmaBot.EXTENSIONS == ("cogs.verify", "cogs.members", "cogs.admin_tools", "cogs.activities", "cogs.db_sync",
                                     "cogs.command_center")


async def test_on_ready_only_runs_setup_once(w, bot, monkeypatch):
    monkeypatch.setattr(type(bot.client), "guilds", property(lambda self: [w.guild]))
    monkeypatch.setattr(bot.client._connection, "user", SimpleNamespace(name="nmabot", id=5), raising=False)
    log = w.guild.add_text_channel("bot-log")
    cc = w.guild.add_text_channel("command-center")
    ready = bot.client.get_cog("CommandCenter")
    ready._ready_once = False  # the cog instance is shared across tests
    await ready.on_ready()
    await ready.on_ready()  # simulated reconnect
    assert len(log.sent) == 1 and len(cc.sent) == 1


async def test_activities_cog_unload_cancels_pending_deletions(bot):
    cancelled = []
    activities_cog = cog(bot)
    activities_cog._pending[1] = SimpleNamespace(cancel=lambda: cancelled.append(1))
    try:
        await activities_cog.cog_unload()
    finally:
        activities_cog._pending.clear()
    assert cancelled == [1]
