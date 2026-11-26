import json
from types import SimpleNamespace

import pytest

from utils import interact
from utils.constants import embed_dict

COURSES = {
    "Computational Tools for Climate Science": "climate",
    "Computational Neuroscience": "cn",
    "Deep Learning": "dl",
    "NeuroAI": "neuroai",
}


def obj(guild_name):
    return SimpleNamespace(guild=SimpleNamespace(name=guild_name))


@pytest.fixture
def pods(data_dir):
    (data_dir / "pods.json").write_text(json.dumps({k: {"id": v} for k, v in COURSES.items()}))


@pytest.mark.parametrize("guild_name,expected", [
    ("Climate Science 2024", "climate"),
    ("CN Test", "cn"),
    ("DL 2024", "dl"),
    ("NeuroAI Summer", "neuroai"),
    ("CN DL", "cn"),  # precedence: CN beats DL
    ("Climate CN", "climate"),  # Climate beats CN
])
def test_guild_pick(pods, guild_name, expected):
    assert interact.guild_pick(obj(guild_name)) == {"id": expected}


def test_guild_pick_unknown_returns_string(pods):
    assert interact.guild_pick(obj("Something Else")) == "Invalid Course"


def test_guild_pick_missing_pods_json(data_dir):
    with pytest.raises(FileNotFoundError):
        interact.guild_pick(obj("CN"))


def test_send_embed_modes(snapshot):
    out = {m: interact.send_embed(m).to_dict() for m in embed_dict}
    out["custom"] = interact.send_embed("custom", "Hello", "World").to_dict()
    out["custom_admin"] = interact.send_embed("custom", "Administrative Notice", "x").to_dict()
    out["custom_defaults"] = interact.send_embed("custom").to_dict()
    snapshot("send_embed", out)


def test_guild_pick_matches_whole_words_only(pods):
    assert interact.guild_pick(obj("CNN Fans")) == "Invalid Course"


def test_guild_pick_allows_digits_next_to_course_code(pods):
    assert interact.guild_pick(obj("NMA2024CN")) == {"id": "cn"}
