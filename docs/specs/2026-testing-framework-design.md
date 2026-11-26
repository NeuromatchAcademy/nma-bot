# Testing framework design (nma-bot)

## Goal
Characterization test suite + CI so current behaviour is preserved unless intentionally changed.

## Approach (my call)
pytest + pytest-asyncio, hand-rolled fakes for discord objects (no network, no DB, no token),
syrupy-style golden snapshots (plain JSON files under tests/snapshots, updated via `--update-snapshots`
flag in conftest; no extra dependency). Bugs found are pinned as current behaviour and marked
`@pytest.mark.known_bug` with a reason, so fixing one intentionally breaks a test you then update.

Rejected: mocking discord.py with unittest.mock only (brittle, hides call shape); dpytest (poor
support for forums/overwrites/scheduled events, lags discord.py 2.x).

## Minimal source changes (approved)
1. `nma-bot.py`: `client.run()` under `if __name__ == "__main__":`; tests load it via `importlib` (filename unchanged).
2. Paths: a `utils/paths.py` with `ROOT`; `config.json`, `pods.json`, `discord-ids.json` resolved from
   ROOT (overridable by `NMA_DATA_DIR` env var; tests point it at tmp_path).
3. `pyproject.toml`: `[dependency-groups] dev = [pytest, pytest-asyncio, pytest-cov, ruff]`.

## Layout
tests/conftest.py        fakes: FakeGuild/Channel/Forum/Member/Role/Message/Interaction, tmp data dir, env
tests/fakes.py
tests/test_db.py         row->pod_data (golden), missing-data, poll_db change detection, save json
tests/test_interact.py   guild_pick per guild name, send_embed all modes (golden)
tests/test_constants.py  activity_index/embed_dict/config.json schema + snapshots
tests/test_activities.py create_activity_invite (aiohttp faked), get_activity_channel naming/recursion, get_activity_event
tests/test_users.py      verify_user success/failure paths, lookup_user, mega_from_pod (recorded calls golden)
tests/test_buttons.py    every Button callback: recorded interaction/permission calls; dropdown->BUTTON_MAPPING
tests/test_administrator.py views/dropdown options
tests/test_bot.py        on_message router (verify, DM, --nma commands incl. broken init/assign), on_voice_state_update, start_activity
tests/snapshots/*.json

## CI
.github/workflows/ci.yml: on push/PR; astral-sh/setup-uv; `uv sync --group dev`; `ruff check` (non-blocking
initially, existing code unlinted); `pytest --cov` with floor set to measured baseline.

## Non-goals
Live Discord/Postgres integration tests; fixing the known bugs; refactoring beyond the above.
