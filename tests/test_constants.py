import json

from tests.conftest import ROOT
from utils import buttons
from utils.constants import activity_index, embed_dict


def test_activity_index_snapshot(snapshot):
    snapshot("activity_index", activity_index)


def test_embed_dict_snapshot(snapshot):
    snapshot("embed_dict", embed_dict)


def test_config_json_snapshot(snapshot):
    snapshot("config_json", json.loads((ROOT / "config.json").read_text()))


def test_activity_index_shape():
    for name, entry in activity_index.items():
        assert set(entry) == {"max", "id"}, name
        assert isinstance(entry["max"], int) and isinstance(entry["id"], int), name


def test_game_dropdown_options_exist_in_activity_index():
    labels = [o.label for o in buttons.GameDropdown(None).options]
    assert labels and all(label in activity_index for label in labels)


def test_slash_command_choices_exist_in_activity_index(snapshot):
    from cogs.activities import Activities
    choices = Activities.start_activity.parameters[0].choices
    snapshot("start_activity_choices", [[c.name, c.value] for c in choices])
    assert all(c.value in activity_index for c in choices)


def test_chat_dropdown_option_not_in_activity_index():
    # known_bug: ChatDropdown offers 'fMRI' which has no activity_index entry
    labels = [o.label for o in buttons.ChatDropdown(None).options]
    assert "fMRI" in labels and "fMRI" not in activity_index
