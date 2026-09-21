# Finish Backend Modular Migration

**Goal:** Move HTTP/WebSocket handlers, realtime delivery, persistence I/O, projections, and distinct game-rule domains out of `main.py` and `game.py` without changing clients or saves.

**Spec:** `docs/superpowers/specs/2026-09-20-vue-vite-modular-migration-design.md`

**Constraints:** Preserve paths, request validation, response bodies, WebSocket messages, save format, and the live 8000 process/save. Work only in the isolated checkout; use temporary game saves for runtime tests.

## Task 1: API boundary

- Add a route-contract test covering every current HTTP route, websocket path, methods, and relevant auth dependency.
- Move request schemas, player/storyteller/chat routes, WebSocket endpoint and QR endpoint to `api/` modules. Move Hub to `application/realtime.py`.
- Keep `main.py` as app assembly and static mount. Preserve import aliases for existing Python tests.
- Run backend unit tests and isolated smoke; commit.

## Task 2: Persistence and projections

- Add tests for atomic save, legacy backup, corrupt-save handling, private-view secrecy, and save reload.
- Move JSON filesystem operations to `infrastructure/persistence.py` while preserving `GameManager.save/load` and `SAVE_PATH` test override.
- Move view composition methods to `application/projections.py`, retaining method compatibility on `GameManager`.
- Run unit and isolated smoke tests; commit.

## Task 3: Rules domains

- Ensure domain regression tests cover chat, nomination, review, and legacy night adapters.
- Move these method groups to focused domain mixins/modules without changing the `GameManager` public method names.
- Keep the canonical night engine in its existing `night/` modules; relocate legacy night compatibility methods into a focused adapter.
- Run backend tests, smoke, and Python compile; commit.

## Task 4: Cleanup and final acceptance

- Delete `frontend/legacy/`, `/legacy`, `/app.js`, and `/styles.css` migration-only server routes after Vue parity is established.
- Update docs and static tests.
- Run frontend tests/build, backend tests, isolated smoke, route/save contract checks, and a local phone-width UI check where tooling allows. Never touch the live service or tunnel.
- Commit and request independent whole-branch review; address important findings and rerun verification.
