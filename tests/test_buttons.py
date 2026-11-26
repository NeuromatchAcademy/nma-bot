import json

import discord
import pytest

from tests.fakes import (
    FakeChannel,
    FakeGuild,
    FakeInteraction,
    FakeMember,
    FakeMessage,
    FakeRole,
    calls_summary,
)
from utils import buttons

COURSE = "Computational Neuroscience"
ROLE_NAMES = ["Organizers", "Staffers", "Robots", "Lead TA", "Teaching Assistant", "Project TA",
              "Approved User", "Alumnus", "TA Alumnus", "americas", "europe-africa", "asia-pacific"]


class W:
    """Test world: guild, invoking user, interaction and helpers."""

    def role(self, name):
        return discord.utils.get(self.guild.roles, name=name)

    def member(self, name, id, *role_names):
        m = FakeMember(name, id, roles=[self.role(r) for r in role_names])
        self.guild.members.append(m)
        return m

    def snap(self, **objs):
        return {k: calls_summary(v) for k, v in objs.items()}

    def say(self, content):
        return self.inter.client.queue_message(content)

    def prompts(self):
        return [c for c in self.inter.response.calls]


@pytest.fixture
def w(data_dir):
    w = W()
    w.data_dir = data_dir
    w.guild = FakeGuild("CN Test", roles=[FakeRole(r) for r in ROLE_NAMES])
    w.log = w.guild.add_text_channel("bot-log")
    w.cc = w.guild.add_text_channel("command-center")
    w.user = w.member("admin", 1, "Organizers", "Staffers", "Lead TA", "Teaching Assistant")
    w.inter = FakeInteraction(user=w.user, guild=w.guild, channel=w.cc)
    (data_dir / "discord-ids.json").write_text("{}")
    return w


def set_pods(w, structure, users=None):
    (w.data_dir / "pods.json").write_text(json.dumps({COURSE: {"structure": structure, "users": users or {}}}))


def embeds(chan):
    return [c[2]["embed"] for c in calls_summary(chan) if c[0] == "send" and "embed" in c[2]]


async def press(cls, w):
    await cls(None).callback(w.inter)


# ---------------------------------------------------------------- meta commands

@pytest.mark.parametrize("roles,text", [
    (["Organizers"], "You do possess administrative powers."),
    ([], "You do not possess administrative powers.")])
async def test_check_authority(w, roles, text):
    w.user.roles = [w.role(r) for r in roles]
    await press(buttons.CheckAuthority, w)
    assert w.inter.response.calls == [("send_message", (f"Hey admin! {text}",), {"ephemeral": True})]


async def test_check_user_details(w, snapshot):
    set_pods(w, {"Alpha": ["Blue Rays"]}, {"sam@x.org": {
        "name": "Sam", "role": "student", "timeslot": "4", "megapods": ["Alpha"], "pods": ["Blue Rays"]}})
    (w.data_dir / "discord-ids.json").write_text(json.dumps({"77": "sam@x.org"}))
    msg = w.say("<@77>")
    await press(buttons.CheckUserDetails, w)
    snapshot("btn_check_user_details", {"prompt": w.inter.response.calls, "channel": calls_summary(w.cc),
                                        "msg": calls_summary(msg)})


async def test_check_user_details_unknown_id_raises(w):
    set_pods(w, {})
    w.say("<@99>")
    with pytest.raises(KeyError):
        await press(buttons.CheckUserDetails, w)


def pod_forum_with_members(w):
    forum = w.guild.add_forum("blue-rays")
    org = w.member("org", 10, "Organizers")
    lead = w.member("lead", 11, "Lead TA", "Teaching Assistant")
    ta = w.member("ta", 12, "Teaching Assistant")
    stu = w.member("stu", 13, "Approved User")
    forum.overwrites = {org: {}, lead: {}, ta: {}, stu: {}, w.guild.default_role: {}}
    return forum


async def test_check_pod_details_labels(w, snapshot):
    pod_forum_with_members(w)
    w.say("blue rays")  # space converted to hyphen
    await press(buttons.CheckPodDetails, w)
    snapshot("btn_check_pod_details", embeds(w.cc))


async def test_check_pod_details_labels_use_member_roles_not_invoker_roles(w):
    pod_forum_with_members(w)
    w.say("blue-rays")
    await press(buttons.CheckPodDetails, w)
    assert embeds(w.cc)[0]["description"] == "**Members:**\nlead **(Lead TA)**\nta **(TA)**\nstu\n"


async def test_check_pod_details_unknown_pod(w):
    w.say("nope")
    await press(buttons.CheckPodDetails, w)
    assert "No pod channel named `nope`" in embeds(w.cc)[0]["description"]


async def test_info_buttons_deny_non_admins(w, monkeypatch):
    monkeypatch.delenv("ADMIN_USER_IDS", raising=False)
    w.inter.user = w.member("plain", 50, "Approved User")
    for cls in (buttons.CheckUserDetails, buttons.CheckPodDetails):
        w.inter.response.calls.clear()
        await press(cls, w)
        (name, _args, kw), = w.inter.response.calls
        assert name == "send_message" and kw["ephemeral"] is True


async def test_check_authority_recognises_super_admins(w, monkeypatch):
    monkeypatch.setenv("ADMIN_USER_IDS", "1")
    w.user.roles = []
    await press(buttons.CheckAuthority, w)
    assert "do possess" in w.inter.response.calls[0][1][0]


async def test_clean_channel_wipes_history_and_reposts_menu(w):
    old = [FakeMessage(f"m{i}", channel=w.cc) for i in range(3)]
    w.cc.history_messages = list(old)
    await press(buttons.CleanChannel, w)
    assert all(calls_summary(m) == [["delete", [], {}]] for m in old)
    sends = [c for c in w.cc.calls if c[0] == "send"]
    assert len(sends) == 1
    assert sends[0][2]["embed"].title == "Administrative Interface"
    assert type(sends[0][2]["view"]).__name__ == "CommandDropdownView"


# ---------------------------------------------------------------- pod commands

@pytest.mark.parametrize("cls,visible", [(buttons.AssignUser, True), (buttons.RemoveUser, False)])
async def test_assign_remove_user(w, cls, visible, snapshot):
    target = w.member("sam", 77)
    a = w.guild.add_text_channel("shiny-corals")
    b = w.guild.add_forum("windy-city")
    w.say("<@77>, Shiny Corals, windy city")
    await press(cls, w)
    snapshot(f"btn_{cls.__name__}", w.snap(shiny=a, windy=b, channel=w.cc))
    assert a.overwrites[target] == {"view_channel": visible, "send_messages": visible}


async def test_assign_user_missing_channel_raises(w):
    w.member("sam", 77)
    w.say("<@77>, nowhere")
    with pytest.raises(AttributeError):
        await press(buttons.AssignUser, w)


def repod_world(w):
    set_pods(w, {"Alpha": ["Blue Rays"]}, {"sam@x.org": {
        "name": "Sam", "role": "student", "timeslot": "4", "megapods": ["Alpha"], "pods": ["Blue Rays"]}})
    (w.data_dir / "discord-ids.json").write_text(json.dumps({"77": "sam@x.org"}))
    sam = w.member("sam", 77)
    cat = w.guild.add_category("alpha")
    social = w.guild.add_category("social")
    thread = FakeChannel("General")
    w.pod = w.guild.add_forum("blue-rays", cat, threads=[thread])
    w.thread = thread
    w.old_forum = w.guild.add_forum("old-pod", cat, overwrites={sam: {}})
    w.gen = w.guild.add_text_channel("alpha-general", cat, members=[sam])
    w.ta = w.guild.add_text_channel("alpha-ta-chat", cat)
    w.chat = w.guild.add_text_channel("chat", social, members=[sam])
    w.orphan = w.guild.add_text_channel("orphan", None, members=[sam])
    return sam


async def test_repod_user_success(w, snapshot):
    repod_world(w)
    w.say("<@77>")
    await press(buttons.RepodUser, w)
    snapshot("btn_repod_success", w.snap(channel=w.cc, pod=w.pod, thread=w.thread, old=w.old_forum,
                                        gen=w.gen, ta=w.ta, social=w.chat, orphan=w.orphan))
    assert w.chat.calls == [] and w.orphan.calls == []  # excluded category / no category untouched


async def test_repod_user_unverified(w):
    set_pods(w, {})
    w.member("sam", 77)
    w.say("<@77>")
    await press(buttons.RepodUser, w)
    assert [e["title"] for e in embeds(w.cc)] == ["Repod Notice"]  # stops: nothing to repod
    assert "has not verified yet" in embeds(w.cc)[0]["description"]


def merge_world(w, pods, mega_old="Alpha", mega_new="Beta"):
    set_pods(w, {mega_old: [pods[0]], mega_new: [pods[1]]})
    ta = w.member("ta", 20, "Teaching Assistant")
    stu = w.member("stu", 21, "Approved User")
    w.old = w.guild.add_forum("shiny-corals", overwrites={ta: {}, stu: {}, w.guild.default_role: {}})
    w.new = w.guild.add_forum("blue-rays")
    for m in ("alpha", "beta"):
        setattr(w, f"{m}_gen", w.guild.add_text_channel(f"{m}-general"))
        setattr(w, f"{m}_ta", w.guild.add_text_channel(f"{m}-ta-chat"))


async def test_merge_pods_across_megapods(w, snapshot):
    merge_world(w, ["shiny corals", "blue rays"])  # lowercase names in pods.json so lookup succeeds
    w.say("Shiny Corals, Blue Rays")
    await press(buttons.MergePods, w)
    snapshot("btn_merge_pods", w.snap(old=w.old, new=w.new, alpha_gen=w.alpha_gen, alpha_ta=w.alpha_ta,
                                      beta_gen=w.beta_gen, beta_ta=w.beta_ta, channel=w.cc))


async def test_merge_pods_capitalised_names_also_move_megapod_perms(w):
    merge_world(w, ["Shiny Corals", "Blue Rays"])
    w.say("Shiny Corals, Blue Rays")
    await press(buttons.MergePods, w)
    for chan in (w.alpha_gen, w.alpha_ta, w.beta_gen, w.beta_ta):
        assert chan.calls != []


# ---------------------------------------------------------------- server commands

async def test_initialize_server(w, snapshot):
    set_pods(w, {"Alpha": ["Blue Rays", "Green Owls"], "Beta": ["Red Fox"]})
    await press(buttons.InitializeServer, w)
    snapshot("btn_initialize_server", {
        "guild": calls_summary(w.guild), "log": embeds(w.log), "response": calls_summary(w.inter.response),
        "forums": {f.name: calls_summary(f) for f in w.guild.forums},
        "channels": sorted(c.name for c in w.guild.channels)})


async def test_initialize_server_skips_existing_megapod(w):
    set_pods(w, {"Alpha": ["Pod1"]})
    cat = w.guild.add_category("Alpha")
    await press(buttons.InitializeServer, w)
    assert [c[0] for c in w.guild.calls] == ["create_forum"]
    assert w.guild.forums[0].category is cat


async def test_initialize_server_twice_does_not_duplicate_multiword_forums(w):
    set_pods(w, {"Alpha": ["Blue Rays"]})
    await press(buttons.InitializeServer, w)
    await press(buttons.InitializeServer, w)
    assert [f.name for f in w.guild.forums] == ["Blue-Rays"]


def graduate_world(w, monkeypatch, authorised=True):
    # Organizers alone are not enough to graduate a server; the invoker's ID must be in ADMIN_USER_IDS
    w.inter.user = w.member("zoltaniam", 2, "Organizers")
    monkeypatch.setenv("ADMIN_USER_IDS", "2" if authorised else "999")
    stu = w.member("stu", 30, "Approved User", "Teaching Assistant")
    admin_cat = w.guild.add_category("Administrative")
    w.log.category = w.cc.category = admin_cat
    cat = w.guild.add_category("alpha")
    social = w.guild.add_category("social")
    w.gen = w.guild.add_text_channel("alpha-general", cat, members=[stu])
    w.pod = w.guild.add_forum("blue-rays", cat)
    w.chat = w.guild.add_text_channel("chat", social, members=[stu])
    w.stu = stu


async def test_graduate_server_unauthorised(w, monkeypatch):
    graduate_world(w, monkeypatch, authorised=False)
    await press(buttons.GraduateServer, w)
    (name, _args, kw), = w.inter.response.calls
    assert name == "send_message" and kw["ephemeral"] is True
    assert "authorised administrators" in kw["embed"].description
    assert w.gen.calls == []


async def test_graduate_server_leaves_categoryless_channels_alone(w, monkeypatch):
    graduate_world(w, monkeypatch)
    w.log.category = None
    await press(buttons.GraduateServer, w)
    assert w.log in w.guild.channels
    assert w.gen not in w.guild.channels  # megapod channels are still purged


async def test_graduate_server_authorised(w, snapshot, monkeypatch):
    graduate_world(w, monkeypatch)
    await press(buttons.GraduateServer, w)
    snapshot("btn_graduate_server", {
        "student": calls_summary(w.stu), "log": embeds(w.log), "channel": embeds(w.cc),
        "remaining": sorted(c.name for c in w.guild.channels),
        "social_untouched": w.chat.calls == []})
    assert len(embeds(w.cc)) == 1


@pytest.mark.parametrize("cls", [
    buttons.CleanChannel, buttons.AssignUser, buttons.RemoveUser, buttons.RepodUser,
    buttons.MergePods, buttons.InitializeServer, buttons.ForceDB, buttons.GraduateServer])
async def test_admin_buttons_deny_non_admins(w, monkeypatch, cls):
    monkeypatch.delenv("ADMIN_USER_IDS", raising=False)
    w.inter.user = w.member("plain", 50, "Approved User")
    await press(cls, w)
    (name, _args, kw), = w.inter.response.calls
    assert name == "send_message" and kw["ephemeral"] is True
    assert kw["embed"].title == "Administrative Notice"
    assert w.guild.calls == [] and w.cc.calls == [] and w.log.calls == []


async def test_force_db(w, monkeypatch):
    called = []

    async def fake_poll():
        called.append(1)

    monkeypatch.setattr(buttons.db, "poll_db", fake_poll)
    await press(buttons.ForceDB, w)
    assert called == [1]
    (_, _, kw), = w.inter.response.calls
    assert kw["embed"].title == "Updated Database"


# ---------------------------------------------------------------- activities

@pytest.mark.parametrize("cls,channel_name,event,blurb", [
    (buttons.StudyTogether, "study", "Study Session", "study session"),
    (buttons.CodeTogether, "code", "Coding Session", "coding session"),
    (buttons.WatchTogether, "Watch Together", "Watch Party", "watch party"),
    (buttons.HangTogether, "hang", "Hang Out", "hangout"),
    (buttons.SampleTopic, "hang", "Hang Out", "hangout"),
])
async def test_activity_buttons(w, monkeypatch, cls, channel_name, event, blurb):
    w.guild.add_category("social")
    soc = w.guild.add_text_channel("social-general")
    invites = []

    async def fake_invite(activity, channel_id):
        invites.append(activity)
        return "abc"

    monkeypatch.setattr(buttons, "create_activity_invite", fake_invite)
    await press(cls, w)
    assert w.inter.response.calls == [
        ("send_message", ("This may take a second. Please be patient, admin!",), {"ephemeral": True})]
    assert [c.name for c in w.guild.voice_channels] == [channel_name]
    assert invites == ["Watch Together" if cls is buttons.WatchTogether else "Jamspace"]
    assert calls_summary(soc) == [["send", [f"Click here to join admin's {blurb}: https://discord.gg/abc"], {}]]
    (ev,) = w.guild.scheduled_events
    assert ev.name == event and ev.calls == [("start", (), {})]


async def test_game_dropdown_callback(w, monkeypatch):
    w.guild.add_category("social")
    gaming = w.guild.add_text_channel("gaming")

    async def fake_invite(game, channel_id):
        return "inv"

    monkeypatch.setattr(buttons, "create_activity_invite", fake_invite)
    d = buttons.GameDropdown(None)
    d._values = ["Scrabble"]
    await d.callback(w.inter)
    assert calls_summary(gaming) == [["send", ["<@1> has started an activity! Click here to join: https://discord.gg/inv"], {}]]
    assert [c.name for c in w.guild.voice_channels] == ["Scrabble"]
    assert w.guild.scheduled_events[0].name == "Scrabble Party"
    assert w.guild.scheduled_events[0].calls == [("start", (), {})]


async def test_chat_dropdown_callback(w):
    w.guild.add_category("social")
    soc = w.guild.add_text_channel("social-general")
    d = buttons.ChatDropdown(None)
    d._values = ["Chess In The Park"]
    await d.callback(w.inter)
    assert [c.name for c in w.guild.voice_channels] == ["Chess In The Park Discussion"]
    assert calls_summary(soc) == [["send", [
        "<@1> has started a discussion on Chess In The Park! Click here to join: https://discord.gg/invite-code"], {}]]
    assert w.guild.scheduled_events[0].calls == [("start", (), {})]


async def test_grab(w):
    msg = w.say("hello")
    assert await buttons.grab("Prompt?", w.inter) is msg
    assert w.inter.response.calls == [("send_message", ("Prompt?",), {"ephemeral": True})]
