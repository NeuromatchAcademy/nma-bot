"""Hand-written fakes for the discord objects the bot touches.

Every fake records mutating calls in `.calls` as (method, args, kwargs);
`calls_summary(obj)` turns that into a JSON-friendly list for snapshots.
`isinstance(fake, discord.Member)` etc. work via the `__class__` property.
"""
import itertools
from types import SimpleNamespace

import discord

_ids = itertools.count(1000)


def _label(v):
    if isinstance(v, discord.Embed):
        return {"title": v.title, "description": v.description,
                "color": v.colour.value if v.colour else None}
    if isinstance(v, discord.File):
        return {"file": v.filename}
    if isinstance(v, _Fake):
        return f"{v._kind}:{v.name}"
    if isinstance(v, (list, tuple)):
        return [_label(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _label(x) for k, x in v.items()}
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    return repr(v)


def calls_summary(obj):
    return [[m, _label(list(a)), _label(dict(k))] for m, a, k in obj.calls]


class _Fake:
    _kind = "Fake"
    _real = None  # discord class that isinstance() should report

    def __init__(self, name=None, id=None):
        self.name = name
        self.id = id if id is not None else next(_ids)
        self.calls = []

    @property
    def __class__(self):  # makes isinstance(fake, discord.X) work
        return self._real or type(self)

    def _rec(self, method, *args, **kwargs):
        self.calls.append((method, args, kwargs))

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return f"<{self._kind} {self.name}>"


class FakeRole(_Fake):
    _kind = "Role"
    _real = discord.Role


class FakeMember(_Fake):
    _kind = "Member"
    _real = discord.Member

    def __init__(self, name, id=None, roles=(), nick=None):
        super().__init__(name, id)
        self.roles = list(roles)
        self.nick = nick

    async def edit(self, **kw):
        self._rec("edit", **kw)
        if "nick" in kw:
            self.nick = kw["nick"]

    async def add_roles(self, *roles, **kw):
        self._rec("add_roles", *roles)
        self.roles.extend(r for r in roles if r not in self.roles)

    async def remove_roles(self, *roles, **kw):
        self._rec("remove_roles", *roles)
        self.roles = [r for r in self.roles if r not in roles]


class FakeMessage(_Fake):
    _kind = "Message"
    _real = discord.Message

    def __init__(self, content, author=None, channel=None, guild=None):
        super().__init__("message")
        self.content = content
        self.author = author
        self.channel = channel
        self.guild = guild if guild is not None else getattr(channel, "guild", None)

    async def delete(self):
        self._rec("delete")


class FakeChannel(_Fake):
    _kind = "Channel"
    _real = discord.TextChannel

    def __init__(self, name, type=discord.ChannelType.text, category=None, members=(),
                 overwrites=None, threads=(), parent=None, guild=None):
        super().__init__(name)
        self.type = type
        self.category = category
        self.members = list(members)
        self.overwrites = dict(overwrites or {})
        self.threads = list(threads)
        self.parent = parent
        self.guild = guild
        self.history_messages = []

    async def send(self, content=None, **kw):
        args = () if content is None else (content,)
        self._rec("send", *args, **kw)
        return FakeMessage(content, channel=self)

    async def set_permissions(self, target, **perms):
        self._rec("set_permissions", target, **perms)
        self.overwrites[target] = perms

    async def delete(self, reason=None):
        self._rec("delete", **({"reason": reason} if reason else {}))
        if self.guild and self in self.guild.channels:
            self.guild.channels.remove(self)

    async def create_invite(self, **kw):
        self._rec("create_invite", **kw)
        return "invite-code"

    async def create_thread(self, **kw):
        self._rec("create_thread", **kw)
        t = FakeChannel(kw.get("name"), type=discord.ChannelType.public_thread, parent=self, guild=self.guild)
        self.threads.append(t)
        return t

    async def history(self, limit=None):
        for m in list(self.history_messages):
            yield m


class FakeForum(FakeChannel):
    _kind = "Forum"
    _real = discord.ForumChannel

    def __init__(self, name, **kw):
        super().__init__(name, type=discord.ChannelType.forum, **kw)


class FakeVoice(FakeChannel):
    _kind = "Voice"
    _real = discord.VoiceChannel

    def __init__(self, name, **kw):
        super().__init__(name, type=discord.ChannelType.voice, **kw)


class FakeDM(FakeChannel):
    _kind = "DM"
    _real = discord.DMChannel

    def __init__(self, name="dm", **kw):
        super().__init__(name, type=discord.ChannelType.private, **kw)


class FakeCategory(_Fake):
    _kind = "Category"
    _real = discord.CategoryChannel

    def __init__(self, name, guild=None):
        super().__init__(name)
        self.type = discord.ChannelType.category
        self.guild = guild
        self.overwrites = {}

    @property
    def channels(self):
        return [c for c in self.guild.channels if c.category is self]

    async def set_permissions(self, target, **perms):
        self._rec("set_permissions", target, **perms)
        self.overwrites[target] = perms

    async def delete(self, reason=None):
        self._rec("delete")
        self.guild.categories_list.remove(self)

    async def create_voice_channel(self, name, **kw):
        return await self.guild.create_voice_channel(name, category=self, **kw)

    async def create_text_channel(self, name, **kw):
        return await self.guild.create_text_channel(name, category=self, **kw)


class FakeEvent(_Fake):
    _kind = "Event"

    def __init__(self, name, **kw):
        super().__init__(name)
        self.kwargs = kw

    async def start(self):
        self._rec("start")


class FakeGuild(_Fake):
    _kind = "Guild"
    _real = discord.Guild

    def __init__(self, name, roles=(), members=()):
        super().__init__(name)
        self.roles = list(roles)
        self.members = list(members)
        self.channels = []
        self.categories_list = []
        self.scheduled_events = []
        self.default_role = FakeRole("@everyone")

    # --- derived views
    @property
    def categories(self):
        return list(self.categories_list)

    @property
    def text_channels(self):
        return [c for c in self.channels if c.type == discord.ChannelType.text]

    @property
    def voice_channels(self):
        return [c for c in self.channels if c.type == discord.ChannelType.voice]

    @property
    def forums(self):
        return [c for c in self.channels if c.type == discord.ChannelType.forum]

    # --- setup helpers (sync)
    def add_category(self, name):
        c = FakeCategory(name, guild=self)
        self.categories_list.append(c)
        return c

    def _add(self, ch, category):
        ch.guild = self
        ch.category = category
        self.channels.append(ch)
        return ch

    def add_text_channel(self, name, category=None, **kw):
        return self._add(FakeChannel(name, **kw), category)

    def add_voice_channel(self, name, category=None, **kw):
        return self._add(FakeVoice(name, **kw), category)

    def add_forum(self, name, category=None, **kw):
        return self._add(FakeForum(name, **kw), category)

    # --- async API mirrored from discord.Guild
    async def create_category(self, name, **kw):
        self._rec("create_category", name, **kw)
        return self.add_category(name)

    async def create_text_channel(self, name, category=None, **kw):
        self._rec("create_text_channel", name, **({"category": category} if category else {}), **kw)
        return self.add_text_channel(name, category)

    async def create_voice_channel(self, name, category=None, **kw):
        self._rec("create_voice_channel", name, **({"category": category} if category else {}), **kw)
        return self.add_voice_channel(name, category)

    async def create_forum(self, name, category=None, **kw):
        self._rec("create_forum", name, **({"category": category} if category else {}), **kw)
        return self.add_forum(name, category)

    async def fetch_member(self, id):
        self._rec("fetch_member", id)
        return discord.utils.get(self.members, id=id)

    async def fetch_scheduled_events(self):
        return list(self.scheduled_events)

    async def create_scheduled_event(self, **kw):
        self._rec("create_scheduled_event", **kw)
        ev = FakeEvent(kw.get("name"), **kw)
        self.scheduled_events.append(ev)
        return ev


class _Response:
    def __init__(self):
        self.calls = []

    async def send_message(self, *a, **kw):
        self.calls.append(("send_message", a, kw))

    async def edit_message(self, *a, **kw):
        self.calls.append(("edit_message", a, kw))


class FakeClient:
    def __init__(self, interaction=None):
        self.queue = []
        self.user = None

    def queue_message(self, content, author=None, channel=None):
        msg = FakeMessage(content, author=author, channel=channel)
        self.queue.append(msg)
        return msg

    async def wait_for(self, event, check=None, **kw):
        return self.queue.pop(0)


class FakeInteraction:
    def __init__(self, user, guild, channel=None):
        self.user = user
        self.guild = guild
        self.channel = channel
        self.response = _Response()
        self.client = FakeClient()
        self.client.user = None
        # grab() filters on author/channel; queued messages default to this user/channel
        _q = self.client.queue_message
        self.client.queue_message = lambda content, author=None, channel=None: _q(
            content, author or user, channel or self.channel)
