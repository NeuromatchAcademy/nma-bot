
from tests.fakes import FakeInteraction
from utils import administrator, buttons


def test_button_mapping_snapshot(snapshot):
    snapshot("button_mapping", {k: [c.__name__ for c in v] for k, v in administrator.BUTTON_MAPPING.items()})


def test_dropdown_options_snapshot(snapshot):
    out = {}
    for mode in ("admin", "social"):
        d = administrator.Dropdown(None, mode)
        out[mode] = {"placeholder": d.placeholder,
                     "options": [[o.label, o.description, str(o.emoji)] for o in d.options]}
    snapshot("dropdown_options", out)


async def test_views_have_one_dropdown():
    for view_cls, mode in ((administrator.CommandDropdownView, "admin"), (administrator.SocialDropdownView, "social")):
        view = view_cls()
        assert view.timeout is None
        assert [type(c).__name__ for c in view.children] == ["Dropdown"]
        assert view.children[0].mode == mode


async def test_dropdown_callback_swaps_buttons(snapshot):
    view = administrator.CommandDropdownView()
    dropdown = view.children[0]
    dropdown._values = ["Pod Commands"]
    inter = FakeInteraction(user=None, guild=None)
    await dropdown.callback(inter)
    assert [c[0] for c in inter.response.calls] == ["edit_message"]
    snapshot("dropdown_pod_commands_children", [
        [type(c).__name__, getattr(c, "label", None)] for c in view.children])


async def test_dropdown_unknown_value_leaves_only_dropdown():
    view = administrator.SocialDropdownView()
    dropdown = view.children[0]
    dropdown._values = ["Nope"]
    await dropdown.callback(FakeInteraction(user=None, guild=None))
    assert [type(c).__name__ for c in view.children] == ["Dropdown"]


async def test_games_mapping_adds_select():
    view = administrator.SocialDropdownView()
    view.children[0]._values = ["Games"]
    await view.children[0].callback(FakeInteraction(user=None, guild=None))
    assert isinstance(view.children[1], buttons.GameDropdown)

