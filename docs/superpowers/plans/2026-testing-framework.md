# Testing Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Characterization test suite + GitHub Actions CI that pins current bot behaviour.

**Architecture:** pytest + pytest-asyncio with hand-written fakes for discord objects, fake DB cursor, JSON golden snapshots. Two tiny source refactors (import-safe entrypoint, root-relative data paths). Known bugs are pinned, not fixed.

**Tech Stack:** Python 3.13.18, uv, pytest, pytest-asyncio, pytest-cov, ruff, discord.py 2.x.

**Spec:** docs/superpowers/specs/2026-testing-framework-design.md

## Global Constraints

- Source stays behaviour-identical; only changes: `client.run` under `__main__`, `utils/paths.py` + path usage, dev dependency group.
- `nma-bot.py` keeps its filename; tests load it with `importlib` (`tests/conftest.py::load_bot()`).
- Data dir override env var: `NMA_DATA_DIR` (default: repo root). Files: `config.json`, `pods.json`, `discord-ids.json`.
- No network, no Postgres, no real token in tests. Set `DISCORD_TOKEN=test` in conftest.
- Snapshots: `tests/snapshots/<name>.json`; rewrite with `pytest --update-snapshots`.
- Known bugs pinned with `@pytest.mark.known_bug("reason")` (registered marker; test asserts the *current* broken behaviour).
- Coverage floor = measured baseline after Task 8 (rounded down to nearest 5).
- Commit after every task.

## Review Focus

- `pods.json` missing / `discord-ids.json` missing or user id absent: `lookup_user` raises KeyError/FileNotFoundError (pin it).
- DB row with NULL TA/lead/project-TA email: `.lower()` raises AttributeError, `poll_db` swallows it and prints (pin it).
- Guild name matching none of Climate/CN/DL/NeuroAI: `guild_pick` returns `'Invalid Course'` string, callers then fail on indexing (pin it).
- Email in `#verify` with different case/whitespace: lowercased but not stripped (pin it).
- Name > 30 chars truncated to 30 for nickname; timeslot not in 1–5 leaves `time_role` unbound (UnboundLocalError caught → "Failed Verification" embed) (pin it).

---

### Task 1: Scaffolding, paths refactor, entrypoint guard

**Files:**
- Create: `utils/paths.py`, `tests/__init__.py`, `tests/conftest.py`, `tests/fakes.py` (empty stub), `tests/test_paths.py`
- Modify: `pyproject.toml`, `utils/users.py`, `utils/interact.py`, `utils/db.py`, `utils/buttons.py`, `nma-bot.py`, `.gitignore`

**Interfaces:**
- Produces: `utils.paths.data_path(name: str) -> pathlib.Path` (reads `NMA_DATA_DIR` at call time; default repo root). conftest fixtures: `data_dir(tmp_path, monkeypatch) -> Path` (sets `NMA_DATA_DIR`, copies real `config.json` in), `snapshot` fixture (`snapshot(name: str, value: Any)` compares to / writes `tests/snapshots/<name>.json` using `json.dumps(sort_keys=True, indent=2, default=str)`), `load_bot() -> module`, marker `known_bug`, option `--update-snapshots`.
- `users.roleKey` currently loads at import → change to `users.load_role_key()` called inside `verify_user`; keep module attr `roleKey` removed (grep for uses).

- [ ] **Step 1:** Add to `pyproject.toml` `[dependency-groups] dev = ["pytest>=8","pytest-asyncio>=0.24","pytest-cov>=5","ruff>=0.6"]` and `[tool.pytest.ini_options] asyncio_mode="auto"`, `testpaths=["tests"]`, markers `known_bug`. Run `uv sync --group dev`.
- [ ] **Step 2:** Write `tests/test_paths.py`: `data_path("x.json") == ROOT/"x.json"` by default; with `NMA_DATA_DIR=tmp` returns `tmp/"x.json"`. Run: FAIL (module missing).
- [ ] **Step 3:** Implement `utils/paths.py`. Replace every `open('config.json'|'pods.json'|'discord-ids.json')` in `users.py`, `interact.py`, `db.py` (`poll_db` read and `save_data_to_json` target), `buttons.py` with `open(data_path(...))`. Note `db.save_data_to_json` already resolves to repo root; route through `data_path` too. Leave `.dbenv`/`.env` loading alone.
- [ ] **Step 4:** In `nma-bot.py` wrap final `client.run(discordToken)` in `if __name__ == "__main__":`. Delete nothing else (trailing dead `activity`/`client` lines stay).
- [ ] **Step 5:** Write conftest pieces above. Add `tests/snapshots/` is tracked; add `.coverage`, `.pytest_cache/` to `.gitignore`.
- [ ] **Step 6:** Run `uv run pytest -q`. Expected: test_paths passes; also `uv run python -c "import importlib.util as u;s=u.spec_from_file_location('b','nma-bot.py');m=u.module_from_spec(s);s.loader.exec_module(m)"` exits 0 without connecting.
- [ ] **Step 7:** Commit `test: scaffolding, root-relative data paths, import-safe entrypoint`.

### Task 2: Fakes

**Files:** Create `tests/fakes.py`, `tests/test_fakes.py`.

**Interfaces — Produces** (all record calls into `self.calls: list[tuple]` as `(method, args, kwargs)` and `discord.utils.get` must work on them, i.e. expose `.name`/`.id`/attributes):
- `FakeRole(name, id=None)`
- `FakeMember(name, id, roles=(), nick=None)`: async `edit(nick=)`, `add_roles(*r)`, `remove_roles(*r)`; `__str__` = name.
- `FakeChannel(name, type=discord.ChannelType.text, category=None, members=(), overwrites=None, threads=())`: async `send(content=None, embed=None, file=None)`, `set_permissions(target, **perms)`, `delete(reason=None)`, `create_invite()`, `history(limit)` async-iter, `create_thread`, `parent`.
- `FakeCategory(name, channels)` with `create_voice_channel`, `create_text_channel`, `create_forum`.
- `FakeGuild(name, channels, roles, members, categories)` with `default_role`, `forums`, `text_channels`, `voice_channels`, `create_*`, `fetch_member`, `fetch_scheduled_events`, `create_scheduled_event`, `scheduled_events`.
- `FakeMessage(content, author, channel, guild)` with async `delete()`.
- `FakeInteraction(user, guild, channel, client)`: `.response.send_message/edit_message` recorded; `client.wait_for` returns queued messages (`interaction.client.queue_message(msg)`).
- `calls_summary(obj) -> list` : JSON-serialisable view (embeds → `{title, description, color}`; members/channels → names).
- Test: `test_fakes.py` verifies `discord.utils.get(guild.roles, name="X")` returns the role, and `set_permissions` is recorded.

- [ ] Steps: write test_fakes (fails) → implement → pass → commit `test: discord fakes`.

### Task 3: constants, interact, administrator (pure parts)

**Files:** Create `tests/test_constants.py`, `tests/test_interact.py`, `tests/test_administrator.py`.

- [ ] **test_constants:** snapshot `activity_index`, `embed_dict`, and `config.json`; assert every `activity_index` entry has int `max`,`id`; every `GameDropdown` option label (instantiate `buttons.GameDropdown(None).options`) and every `start_activity` choice value is a key in `activity_index` (pin: `ChatDropdown` includes label `fMRI` which is NOT in `activity_index` → `known_bug`).
- [ ] **test_interact:** `guild_pick` parametrized over guild names → `"Climate Science"`→Climate course, `"CN 2024"`, `"DL"`, `"NeuroAI"` (pods.json written in `data_dir`), unknown → `'Invalid Course'`; note precedence order Climate>CN>DL>NeuroAI (guild name `"CN DL"` → CN). `send_embed` for each mode in `embed_dict` + custom with/without `'Administrative'` in title (snapshot embed `to_dict()`; author name `Neuromatch Bot`).
- [ ] **test_administrator:** snapshot Dropdown options for modes `admin` and `social`; `BUTTON_MAPPING` keys and class names; Dropdown.callback swaps view items for "Pod Commands" (fake interaction; assert `edit_message` called, item labels snapshot); `rollcallGen(["a","b"]) == "\na\nb"`.
- [ ] Run, commit `test: constants, interact, administrator`.

### Task 4: db

**Files:** Create `tests/test_db.py`.

**Interfaces:** `FakeConnection(rows)` / `FakeCursor` local to test file (context-manager `cursor()`, `execute(q)` records query, `fetchall()` returns rows). Row = 16-tuple as indexed in `get_pod_data_from_db`.

- [ ] Tests: (a) two pods in one megapod / two courses / shared TA across pods → snapshot of `get_pod_data_from_db` output; emails lowercased; role of a person who is both TA and student keeps first-seen role. (b) executed SQL snapshot (guards accidental query change). (c) `known_bug`: row with `None` TA email raises `AttributeError`. (d) `poll_db.coro` (call `db.poll_db.coro()`) with monkeypatched `connect_to_db` yielding FakeConnection: writes `pods.json` when changed, leaves file mtime untouched when equal, prints `Error occurred while getting data` when `pods.json` missing (`known_bug`? no—pin as behaviour: first run never creates the file). (e) `save_data_to_json` writes to `data_dir`. (f) `connect_to_db` passes env PG_* to monkeypatched `psycopg2.connect` and closes connection.
- [ ] Commit `test: db`.

### Task 5: activities

**Files:** Create `tests/test_activities.py`.

- [ ] Tests: `create_activity_invite` with aiohttp session monkeypatched (fake `ClientSession().post` async-ctx returning status/json): 200 → returns code and posts body `{'max_age':0,'target_type':2,'target_application_id':<id>}` with header `Bot test`; non-200 → returns `None`; unknown activity → `KeyError`. `get_activity_channel`: parametrized name logic (`title='' count=0`→activity, title only, count only `"X-2"`, both); creates voice channel in `social` category when absent; reuses when `len(members) < max` or `max == 0`; recurses to `-1`,`-2` when full (`Putt Party` max 1). `get_activity_event`: creates event when none / name not present (assert kwargs incl. `entity_type=voice`, privacy guild_only, start ≈ now+60s via monkeypatched `discord.utils.utcnow`); returns existing otherwise.
- [ ] Commit `test: activities`.

### Task 6: users (verify flow)

**Files:** Create `tests/test_users.py`.

- [ ] Fixtures: guild named `"CN Test"` with channels `bot-log`, pod forum `blue-rays` (thread `General`), `alpha-general`, `alpha-ta-chat`; roles from config; pods.json with student/ta/lead_ta/project_ta users; `discord-ids.json` empty `{}`.
- [ ] Tests: `verify_user` happy path per role (parametrize 4 roles): snapshot `calls_summary` of user, pod channel, megapod channels, bot-log embeds; nickname truncated at 30; `discord-ids.json` updated with `{str? int?}` key (pin: written key becomes string after json dump); student gets no TA-chat announcement; timeslot→time role for 1..5 (`4,5`→americas, `3`→europe-africa, `1,2`→asia-pacific); unknown email → "Failed Verification" embed with reason `User information not found for this course.`; missing channel (None) → generic "Failed Verification" with error text; bad timeslot `'9'` → Failed Verification (UnboundLocalError text) and **roles already assigned** (pin partial side effects). Email with surrounding space not found (pin). `lookup_user` happy/KeyError; `mega_from_pod` matches `pod` and `pod.replace('-',' ')`, else `'Pod not found'`.
- [ ] Commit `test: users`.

### Task 7: buttons

**Files:** Create `tests/test_buttons.py`.

- [ ] One parametrized/individual test per button callback using FakeInteraction and queued `grab` messages: CheckAuthority (organizer vs not, ephemeral text), CheckUserDetails (embed text snapshot; unknown id → KeyError pin), CheckPodDetails (space→hyphen, Lead TA/TA labels, excludes Organizers/Staffers), CleanChannel (`known_bug`: raises `SystemExit`), AssignUser/RemoveUser (perms calls snapshot; `', '` split; lowercasing), RepodUser (not-verified path + success path snapshot; excluded categories untouched), MergePods (TA vs non-TA manage perm; same vs different megapod), InitializeServer (creates categories/channels/forums/threads Off-Topic, Coursework, General; skips existing), GraduateServer (non-authorised user → refusal; authorised → roles/deletes snapshot), ForceDB (monkeypatch `db.poll_db`), Study/Code/Watch/HangTogether/SampleTopic (monkeypatch `create_activity_invite` → `"abc"`; assert invite URL message to `social-general` and `act_event.start()`), GameDropdown.callback, ChatDropdown.callback, `grab`.
- [ ] Monkeypatch targets live in `utils.buttons` namespace (`buttons.create_activity_invite`, etc.).
- [ ] Commit `test: buttons`.

### Task 8: bot entrypoint (on_message, slash command, voice) + CI

**Files:** Create `tests/test_bot.py`, `.github/workflows/ci.yml`; Modify `pyproject.toml` (coverage floor), `README.md` (Testing section).

- [ ] `load_bot()` fixture-scoped; monkeypatch `bot.client` internals as needed (`message.author != self.user` — set `nmaClient.user` via `client._connection.user` stub or patch property).
- [ ] Tests for `nmaClient.on_message`: verify channel + `@` → `users.verify_user` called then message deleted; verify without `@` → deleted only; DM channel → pin current behaviour (`interact.send_embed(message,'dm')` is called with wrong args → `known_bug`, raises); non-command text ignored; `--nma auth` admin/non-admin text; `--nma identify lgbtq,gender` sets perms on named channels and deletes; `--nma podcheck` in forum vs `-general` text channel (snapshot embed); `--nma getposts` with `#<id>` and name forms writes `<name>-log.csv` to cwd (use `monkeypatch.chdir(tmp_path)`) and sends file; error path embed; `--nma timefix` mapping; `--nma init|assign|unassign|merge|swap` as admin → `known_bug` AttributeError (`administrator.initialize_server`/`pod_change` missing); non-admin → silently ignored. Own messages ignored unless start with `--csrun `.
- [ ] `start_activity` command (`start_activity.callback`): disallowed categories → "only in megapod channels"; allowed → creates `megapod-games` voice channel with default_role hidden and per-member view perms excluding privileged roles; posts invite link (monkeypatch `activities.create_activity_invite`). Choices snapshot (`start_activity.parameters[0].choices`).
- [ ] `on_voice_state_update`: only category `social`, empty, name without `Social Voice Chat` schedules `delete_channel_after` (monkeypatch `client.loop.create_task` capture). `delete_channel_after` with `asyncio.sleep` patched: deletes if empty & exists; skips if repopulated; "User deleted" if gone.
- [ ] `on_ready`: clears/pins messages in `command-center`, `verify`, `activity-center`; restart embed in `bot-log`; `tree.sync` patched.
- [ ] Run `uv run pytest --cov=utils --cov-report=term-missing`; record total; add `[tool.coverage.report] fail_under = <floor>`.
- [ ] CI `.github/workflows/ci.yml`: triggers `push` (main) + `pull_request`; steps `actions/checkout@v4`, `astral-sh/setup-uv@v5`, `uv sync --group dev`, `uv run ruff check . || true` (continue-on-error), `uv run pytest --cov=utils --cov=nma-bot`. Python from `.python-version`.
- [ ] README: "Testing" section (`uv run pytest`, `--update-snapshots`, `known_bug` meaning).
- [ ] Commit `ci: add GitHub Actions workflow and coverage floor`.

## Self-Review notes
Spec coverage: layout files all mapped (constants/interact/administrator→T3, db→T4, activities→T5, users→T6, buttons→T7, bot→T8, CI→T8, paths/deps→T1, fakes→T2). Spec item "nma_bot shim" dropped in favour of importlib (stated in constraints).
