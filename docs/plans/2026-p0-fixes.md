# P0 Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Remove dead/crashing paths, make cold start work, tighten admin gating and stop leaking PII/tracebacks, fix CI coverage target.

**Architecture:** Small, independent commits on the existing flat layout (no cogs yet; that is the next plan). Existing characterization tests are flipped from `known_bug` to real assertions where behaviour changes.

**Tech Stack:** Python 3.13, discord.py 2.x, pytest (+asyncio), ruff, uv.

**Spec:** Agreed in conversation (review of 2026-05, "first batch" design); no separate spec file.

## Global Constraints

- `uv run pytest` and `uv run ruff check .` must pass after every task.
- Coverage floor stays `fail_under = 95`.
- Admin IDs come from env var `ADMIN_USER_IDS` (comma-separated ints) in `.env`; admin role name stays `Organizers`.
- Remaining `--nma` text commands (`identify`, `auth`, `podcheck`, `getposts`, `timefix`) are untouched.

## Review Focus

- `--nma` with no subcommand → ignored, no exception.
- `ADMIN_USER_IDS` unset/empty/garbage → nobody is an ID-admin (never crashes, never grants).
- `pods.json` missing, empty or invalid JSON on first poll → file is created.
- DB unreachable → `poll_db` logs and survives to next tick.
- Non-admin presses an admin button → ephemeral denial, no side effects.

---

### Task 1: Remove dead text commands, DM branch; guard bare `--nma`; restore CleanChannel

**Files:** Modify `nma-bot.py`, `utils/buttons.py`, `README.md`, `tests/test_bot.py`, `tests/test_buttons.py`

- [ ] Flip tests: `test_dm_branch_raises` → DM message produces no calls and no exception; `test_bare_nma_raises` → `--nma` is ignored; delete `test_admin_commands_broken_for_admin`; remove `init/assign/unassign/merge/swap` from the non-admin parametrize; `test_clean_channel_exits` → CleanChannel deletes channel history and re-sends `master` embed with a `CommandDropdownView`.
- [ ] Run; confirm they fail.
- [ ] `nma-bot.py`: drop the DM `elif`, drop the `init`/`assign…` branch, guard `len(msg_cmd) < 2`. Keep `auth`, `identify`, etc. (guard `identify`/`getposts` missing arg with `len` check too).
- [ ] `utils/buttons.py`: `CleanChannel.callback` = delete last 200 messages then `channel.send(embed=send_embed('master'), view=administrator.CommandDropdownView())`. Avoid circular import (import inside callback).
- [ ] README: remove "add a command in on_message / `--nma yourcommand`" guidance, replace with slash-command pointer.
- [ ] Tests + ruff pass; commit `fix: remove dead --nma commands and DM branch, restore CleanChannel`.

### Task 2: `poll_db` cold start and resilience

**Files:** Modify `utils/db.py`, `tests/test_db.py`

- [ ] Tests: missing `pods.json` → file created with polled data; invalid JSON → treated as `{}` and overwritten; `connect_to_db` raising → logged, no exception.
- [ ] Implement `_load_pods(path) -> dict` (missing/invalid → `{}`); move `connect_to_db()` inside `try`.
- [ ] Commit `fix: poll_db survives missing pods.json and DB outages`.

### Task 3: (DROPPED) CI coverage target — verified `--cov=nma_bot` already measures nma-bot.py

**Files:** Modify `.github/workflows/ci.yml`, `README.md`

- [ ] Verify locally `uv run pytest --cov=utils --cov=nma_bot` reports nma_bot (it uses `spec_from_file_location`, so coverage by module name may not work); if not, use `--cov=utils --cov=.` with `--cov-config` omit for tests/.venv, or a `[tool.coverage.run] source`/`include` entry in `pyproject.toml` that includes `nma-bot.py`.
- [ ] Apply the working flags to CI and README; commit `ci: measure nma-bot.py coverage`.

### Task 4: Admin gating

**Files:** Create `utils/auth.py`, `tests/test_auth.py`; Modify `utils/buttons.py`, `tests/test_buttons.py`, `README.md`

**Interfaces:**
- Produces: `admin_ids() -> set[int]` (parses `ADMIN_USER_IDS`), `is_admin(member) -> bool` (id in `admin_ids()` or has role `Organizers`), `is_super_admin(member) -> bool` (id in `admin_ids()` only), `async def require_admin(interaction, *, super_admin=False) -> bool` (sends ephemeral denial and returns False when not allowed).

- [ ] Tests for the above (unset, empty, garbage like `"a,1, 2"` → `{1,2}`; role match; denial message sent).
- [ ] Implement `utils/auth.py`.
- [ ] Apply `require_admin` at the top of: AssignUser, RemoveUser, RepodUser, MergePods, InitializeServer, ForceDB, CleanChannel. `GraduateServer` uses `super_admin=True` replacing the username check and its message ("only authorised administrators…").
- [ ] Update button tests: default fixture user is admin; add one non-admin denial test per button group.
- [ ] Commit `feat: ID/role-based admin gating for admin buttons`.

### Task 5: Stop leaking PII and tracebacks to Discord

**Files:** Modify `utils/users.py`, `nma-bot.py`, `tests/test_users.py`, `tests/test_bot.py`; Create nothing

- [ ] Tests: verification debug embed no longer contains `userInfo`; failure embed shows a generic reason for unexpected exceptions (still shows the `ValueError` text for "not found") and the real exception goes to `logging`; `getposts`/`timefix` error embeds contain no file/line info.
- [ ] Implement: add `log = logging.getLogger(__name__)` in `users.py` and `nma-bot.py`; remove the "Verification DEBUG" embed (log at debug level instead); replace `error`/traceback strings with generic text plus `log.exception`. Call `logging.basicConfig(level=INFO)` in `__main__`.
- [ ] Commit `fix: log errors instead of posting internals and PII to Discord`.

> **Revision (Task 5):** `bot-log` is staff-only, so the "Verification DEBUG" embed and the detailed
> "Ran into this issue: {error}" failure text were restored there. Errors are still also written to
> `logging`. Only the invoking-channel messages for `getposts`/`timefix` stay generic.
