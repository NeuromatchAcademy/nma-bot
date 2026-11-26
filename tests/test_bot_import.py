from tests.conftest import load_bot


def test_import_does_not_run_client():
    bot = load_bot()
    assert bot.client.is_closed() is False
    assert bot.client.user is None
