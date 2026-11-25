import discord

from tests.fakes import (FakeChannel, FakeGuild, FakeInteraction, FakeMember, FakeRole,
                         calls_summary)


async def test_utils_get_and_recording():
    role = FakeRole("Approved User")
    guild = FakeGuild("CN Test", roles=[role])
    chan = guild.add_text_channel("general")
    member = FakeMember("alice", 1, roles=[role])
    assert discord.utils.get(guild.roles, name="Approved User") is role
    assert discord.utils.get(guild.channels, name="general") is chan
    await chan.set_permissions(member, view_channel=True)
    assert calls_summary(chan) == [["set_permissions", ["Member:alice"], {"view_channel": True}]]
    assert member in chan.overwrites


async def test_isinstance_member_and_embeds():
    member = FakeMember("bob", 2)
    assert isinstance(member, discord.Member)
    chan = FakeChannel("c")
    await chan.send(embed=discord.Embed(title="T", description="D", color=0xFF8800))
    assert calls_summary(chan) == [["send", [], {"embed": {"title": "T", "description": "D", "color": 0xFF8800}}]]


async def test_interaction_grab_queue_and_category_creation():
    guild = FakeGuild("g")
    cat = guild.add_category("social")
    vc = await cat.create_voice_channel("v")
    assert vc in guild.channels and vc.category is cat and vc in cat.channels
    user = FakeMember("u", 3)
    inter = FakeInteraction(user=user, guild=guild, channel=vc)
    msg = inter.client.queue_message("hello")
    assert await inter.client.wait_for("message", check=lambda m: True) is msg
    await inter.response.send_message("x", ephemeral=True)
    assert calls_summary(inter.response) == [["send_message", ["x"], {"ephemeral": True}]]
