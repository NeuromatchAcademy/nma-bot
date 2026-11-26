# Cogs Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Split `nma-bot.py` into discord.py cogs, behaviour-preserving, one concern per commit.

**Architecture:** `nma-bot.py` stays the entry file (a systemd unit runs it by name) and defines `NmaBot(commands.Bot)`, whose `setup_hook` loads extensions listed in `EXTENSIONS`. Each extension in the new top-level `cogs/` package exposes `async def setup(bot)`. `utils/` is unchanged except where a task says so. Module-level `client` (the bot) and `tree` (`client.tree`) stay so existing tests keep working.

**Tech Stack:** Python 3.13, discord.py 2.x (`discord.ext.commands`), pytest.

**Spec:** Agreed in conversation (option 1, "incremental, in place"). Package rename is out of scope.

## Global Constraints

- `uv run pytest` (with `--cov=utils --cov=nma_bot --cov=cogs`, floor 95) and `uv run ruff check .` pass after every task; snapshots do not change unless a task says so.
- Behaviour preserved exactly, including: only `--csrun ` prefixed messages from the bot itself are processed (`author != bot.user or content.startswith("--csrun ")`); DMs ignored; in `#verify` messages are never treated as `--nma` commands.
- Intents unchanged. Bot presence "Studying brains..." (watching) is now actually applied (previously unreachable code after `client.run`).
- `command_prefix=commands.when_mentioned` (no prefix commands are used).

## Review Focus

- A message in `#verify` containing `--nma auth` must only be verified/deleted, never run as a command (two listeners now see every message).
- A bot-authored non-`--csrun` message triggers no listener.
- `on_ready` firing twice (reconnect) must not crash and must not start a second `poll_db`.
- Unloading a cog stops `poll_db`.
- `/start_activity` still registered on the tree after sync.

---

### Task 1: `NmaBot` skeleton on `commands.Bot`

**Files:** Modify `nma-bot.py`, `tests/test_bot.py`, `tests/conftest.py`

**Interfaces:**
- Produces: `class NmaBot(commands.Bot)` with `EXTENSIONS: tuple[str, ...]` and `setup_hook`; module vars `client: NmaBot`, `tree = client.tree`; test helper `W.send` dispatches via `client.extra_events["on_message"]` listeners plus the bot's own `on_message` during the transition (until Task 6 removes it).

- [ ] Test: `isinstance(bot.client, commands.Bot)`, `bot.client.activity.name == "Studying brains..."`, `setup_hook` loads every name in `EXTENSIONS` (monkeypatch `load_extension`).
- [ ] Implement: replace `nmaClient(discord.Client)` with `NmaBot(commands.Bot)`; `intents` unchanged; pass `activity=discord.Activity(...)`; delete the dead code after `client.run`. Keep `on_ready`/`on_message`/voice handlers in place for now.
- [ ] Remove `tree = app_commands.CommandTree(client)`; use `client.tree` and `tree.add_command(start_activity)`.
- [ ] Commit `refactor: run on commands.Bot`.

### Task 2: `cogs/verify.py`

**Files:** Create `cogs/__init__.py`, `cogs/verify.py`; Modify `nma-bot.py`, `tests/test_bot.py`; Create `tests/test_cog_verify.py` (move the two `#verify` tests here)

**Interfaces:**
- Produces: `class Verify(commands.Cog)` with listener `on_message(message)`; shared helper `cogs/_common.py::should_handle(bot, message) -> bool` implementing the author/`--csrun` gate; `async def setup(bot)`.

- [ ] Move the `#verify` branch (email → `users.verify_user` then delete; otherwise delete). Also `return` early for DMs (`isinstance(message.channel, discord.DMChannel)`).
- [ ] Test the Review Focus item: `#verify` + `--nma auth` from an admin produces only `delete`, no `auth status` message (requires Task 3's cog to be loaded in that test; add it there).
- [ ] Add `"cogs.verify"` to `EXTENSIONS`; delete the branch from `nma-bot.py`. Commit `refactor: verify cog`.

### Task 3: `cogs/admin_tools.py`

**Files:** Create `cogs/admin_tools.py`, `tests/test_cog_admin_tools.py` (move the `--nma` tests from `test_bot.py` unchanged apart from the helper); Modify `nma-bot.py`

**Interfaces:**
- Produces: `class AdminTools(commands.Cog)`, listener `on_message`; skips when `should_handle` is false, in DMs, and in channels named `verify`. Methods `_identify`, `_podcheck`, `_getposts`, `_timefix`, `_auth` (one per subcommand) called from a small dispatch dict, replacing the if/elif chain. Extract the duplicated podcheck member loop into `_describe_members(guild, members) -> str`.

- [ ] Move tests first (they must fail on import until the cog exists), then move code, then run all tests green (snapshots unchanged).
- [ ] Commit `refactor: admin tools cog`.

### Task 4: `cogs/activities.py`

**Files:** Create `cogs/activities.py`, `tests/test_cog_activities.py` (move slash-command and voice tests); Modify `nma-bot.py`

**Interfaces:**
- Produces: `class Activities(commands.Cog)` with `start_activity` app command (same name, description, choices), listener `on_voice_state_update`, method `delete_channel_after(vc)`. `cog_load` adds the command to the tree implicitly via `@app_commands.command` in the cog (no `tree.add_command`).

- [ ] Move code; keep the `PROTECTED_CATEGORIES` list as a module constant used by `start_activity` (the same list is duplicated in `buttons.GraduateServer`: import it from `utils/constants.py` in both places).
- [ ] Tests call `cog.start_activity.callback(cog, inter, choice())`.
- [ ] Commit `refactor: activities cog`.

### Task 5: `cogs/db_sync.py`

**Files:** Create `cogs/db_sync.py`, `tests/test_cog_db_sync.py`; Modify `utils/db.py`, `nma-bot.py`, `tests/test_db.py`, `tests/test_bot.py`

**Interfaces:**
- Produces: `class DbSync(commands.Cog)` whose `cog_load` starts `db.poll_db` if not running and `cog_unload` cancels it. `utils/db.poll_db` loses its `before_loop` `sleep(20)`; the cog's `before_loop` awaits `bot.wait_until_ready()` instead (set via `db.poll_db.before_loop` replaced by a method on the cog).

- [ ] Tests: loading starts the loop once (second `cog_load` is a no-op), unloading cancels it, `ForceDB` button still works.
- [ ] Remove `setup_hook`'s `poll_db.start()` and its test. Commit `refactor: db sync cog, wait for bot instead of sleeping`.

### Task 6: `cogs/command_center.py`

**Files:** Create `cogs/command_center.py`, `tests/test_cog_command_center.py`; Modify `utils/buttons.py`, `nma-bot.py`

**Interfaces:**
- Produces: `async def reset_channel(channel, *, embed, view=None, pin=True) -> discord.Message` in `utils/interact.py` (wipe last 200 messages, send, pin); `class CommandCenter(commands.Cog)` with listener `on_ready` that syncs the tree and sets up `command-center`, `verify`, `activity-center`, `bot-log` exactly as before (snapshot `on_ready.json` unchanged).
- `buttons.CleanChannel` calls `reset_channel`.

- [ ] `on_ready` is guarded so a reconnect re-runs it safely (tree sync + channel reset are idempotent; the "restart" notice posts only on the first ready — test with a `_ready_once` flag).
- [ ] Delete `nmaClient.on_ready`/`on_message` leftovers. Commit `refactor: command center cog and reset_channel helper`.

### Task 7: Thin entrypoint and docs

**Files:** Modify `nma-bot.py`, `README.md`, `.github/workflows/ci.yml`, `utils/administrator.py`

- [ ] `nma-bot.py` ≈ 40 lines: env loading, `NmaBot`, `EXTENSIONS`, `__main__`.
- [ ] Remove dead code: `administrator.rollcallGen`, commented-out dropdown block, `buttons` commented loader at the top.
- [ ] CI and README: add `--cov=cogs`; README "How to add a command" shows a cog example and how to register it in `EXTENSIONS`.
- [ ] Commit `refactor: thin entrypoint, docs`.

### Task 8: Installable package layout (after Task 7)

**Files:** Move `nma-bot.py` → `nma_bot/__main__.py` + `nma_bot/bot.py`; move `utils/`, `cogs/` into `nma_bot/`; Modify `pyproject.toml`, `tests/conftest.py`, README, CI

- [ ] Add `[build-system]` and `[project.scripts] nma-bot = "nma_bot.__main__:main"`; keep a tiny `nma-bot.py` shim calling `main()` so the systemd unit keeps working until updated.
- [ ] Update imports, drop the `load_bot()` loader hack, use `--cov=nma_bot`.
- [ ] Not for PyPI/distribution: this is an application, deployed from a checkout.

> Note: moved tests for Tasks 2-6 stay in `tests/test_bot.py` (shared `w` fixture) instead of per-cog files.
