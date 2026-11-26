import pytest

from tests.fakes import FakeGuild, FakeInteraction, FakeMember, FakeRole
from utils import auth


@pytest.mark.parametrize("raw,expected", [
    (None, set()),
    ("", set()),
    ("  ", set()),
    ("5", {5}),
    ("a,1, 2,,x3", {1, 2}),
])
def test_admin_ids_parsing(monkeypatch, raw, expected):
    if raw is None:
        monkeypatch.delenv("ADMIN_USER_IDS", raising=False)
    else:
        monkeypatch.setenv("ADMIN_USER_IDS", raw)
    assert auth.admin_ids() == expected


def test_is_admin_by_role_or_id(monkeypatch):
    monkeypatch.setenv("ADMIN_USER_IDS", "7")
    org = FakeRole("Organizers")
    assert auth.is_admin(FakeMember("a", 1, roles=[org]))
    assert auth.is_admin(FakeMember("b", 7))
    assert not auth.is_admin(FakeMember("c", 2, roles=[FakeRole("Staffers")]))


def test_super_admin_requires_id_not_role(monkeypatch):
    monkeypatch.setenv("ADMIN_USER_IDS", "7")
    assert auth.is_super_admin(FakeMember("b", 7))
    assert not auth.is_super_admin(FakeMember("a", 1, roles=[FakeRole("Organizers")]))


@pytest.mark.parametrize("super_admin", [False, True])
async def test_require_admin_denies_with_ephemeral_notice(monkeypatch, super_admin):
    monkeypatch.delenv("ADMIN_USER_IDS", raising=False)
    inter = FakeInteraction(user=FakeMember("p", 2), guild=FakeGuild("g"))
    assert await auth.require_admin(inter, super_admin=super_admin) is False
    (name, _args, kw), = inter.response.calls
    assert name == "send_message" and kw["ephemeral"] is True
    assert kw["embed"].title == "Administrative Notice"


async def test_require_admin_allows_silently(monkeypatch):
    monkeypatch.setenv("ADMIN_USER_IDS", "7")
    inter = FakeInteraction(user=FakeMember("b", 7), guild=FakeGuild("g"))
    assert await auth.require_admin(inter, super_admin=True) is True
    assert inter.response.calls == []
