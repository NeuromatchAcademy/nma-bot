from tests.fakes import FakeChannel, FakeMessage, calls_summary
from utils import interact


async def test_reset_channel_wipes_posts_and_pins():
    chan = FakeChannel("c")
    old = [FakeMessage("a"), FakeMessage("b")]
    chan.history_messages = list(old)
    msg = await interact.reset_channel(chan, embed="E", view="V")
    assert all(calls_summary(m) == [["delete", [], {}]] for m in old)
    assert chan.calls == [("send", (), {"embed": "E", "view": "V"})]
    assert calls_summary(msg) == [["pin", [], {}]]


async def test_reset_channel_without_view_or_pin():
    chan = FakeChannel("c")
    msg = await interact.reset_channel(chan, embed="E", pin=False)
    assert chan.calls == [("send", (), {"embed": "E"})]
    assert msg.calls == []
