# Storyteller Lobby Setup Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate script/player configuration, random and manual role assignment, fabled roles, Sentinel adjustment, and forced start into the Vue storyteller preview.

**Architecture:** Keep `StorytellerLiveView` as the sole owner of the WebSocket projection and route authenticated mutations through a focused storyteller service plus a command composable. Keep manual role assignment as an isolated local draft presented through the grimoire and right context panel; every committed server state continues to arrive through the existing WebSocket view.

**Tech Stack:** Vue 3 Composition API, Vite 8, native Fetch/WebSocket, Vitest 5, Vue Test Utils, existing FastAPI endpoints.

**Spec:** `docs/superpowers/specs/2026-09-20-storyteller-lobby-setup-design.md`

## Global Constraints

- Keep `/#/storyteller` routed to `/legacy/#/storyteller`.
- Add lobby mutations only to `/#/storyteller-preview`.
- Do not change backend behavior, REST/WebSocket contracts, local-storage keys, or JSON save compatibility.
- Keep the existing `1366x768` desktop shell and prevent document-level scrolling.
- Treat REST responses as acknowledgements and the WebSocket projection as authoritative.
- Disable writes while disconnected or reconnecting; keep the latest view visible.
- Configuration changes and random assignment require two explicit actions.
- Per the user's explicit direction, finish all migration code before adding or running tests; run verification once as a consolidated final phase.

## Review Focus

- A fast server projection can arrive before a REST promise resolves; pending state must still settle without overwriting the newer view.
- Reconnection must disable every setup mutation while preserving an in-progress manual draft for inspection.
- A configuration projection that changes script or player count must discard an incompatible manual draft.
- Manual validation must enforce exactly one demon and at least one minion, while treating other composition differences as warnings rather than new prohibitions.
- Entering `playing` must remove every lobby mutation even if an earlier control still has a pending request.

---

### Task 1: Add Authenticated Storyteller Commands

**Files:**
- Create: `frontend/src/services/storyteller.js`
- Create: `frontend/src/composables/useStorytellerCommand.js`

**Interfaces:**
- Consumes: `api(path, init)` and the current storyteller password.
- Produces: `createStorytellerService(password)` with `configure`, `assignRandom`, `assignManual`, `setSentinel`, `toggleFabled`, and `start`; `useStorytellerCommand({ connected })` with `pending`, `error`, `run`, and `clearError`.

- [ ] **Step 1: Create the authenticated service**

Implement a small command factory that adds `X-Storyteller-Password` and exact existing payloads:

```js
import { api } from './api.js'

export function createStorytellerService(password) {
  const command = (path, body) => api(path, {
    method: 'POST',
    headers: { 'X-Storyteller-Password': password },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  })
  return {
    configure: (script, playerCount) => command('/api/config', { script, player_count: playerCount }),
    assignRandom: () => command('/api/assign'),
    assignManual: (draft) => command('/api/assign/manual', draft),
    setSentinel: (value) => command('/api/sentinel', { value }),
    toggleFabled: (id, on) => command('/api/fabled', { id, on }),
    start: () => command('/api/start'),
  }
}
```

- [ ] **Step 2: Create command state ownership**

`useStorytellerCommand` accepts a computed/ref connection predicate, refuses writes with `连接中，暂时不能操作`, records only the active command key, clears errors before each attempt, and always clears pending in `finally`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/storyteller.js frontend/src/composables/useStorytellerCommand.js
git commit -m "feat: add storyteller lobby commands"
```

---

### Task 2: Add Lobby Setup and Advanced Settings

**Files:**
- Create: `frontend/src/components/storyteller/LobbySetupPanel.vue`
- Create: `frontend/src/components/storyteller/SetupControls.vue`
- Create: `frontend/src/components/storyteller/AdvancedSettings.vue`
- Create: `frontend/src/components/storyteller/ConfirmAction.vue`
- Modify: `frontend/src/components/storyteller/GameControlPanel.vue`
- Modify: `frontend/src/styles/storyteller.css`

**Interfaces:**
- Consumes: current `view`, `connected`, `pending`, and emitted command callbacks.
- Produces: `configure({ script, playerCount })`, `set-sentinel(value)`, and `toggle-fabled({ id, on })` intents.

- [ ] **Step 1: Implement reusable two-step confirmation**

`ConfirmAction` receives `label`, `confirmLabel`, `disabled`, and `summary`, arms for three seconds on the first click, emits `confirm` only on the second click, and disarms whenever `summary` changes.

- [ ] **Step 2: Implement destructive configuration editing**

`SetupControls` keeps proposed script and player count locally, clamps count to the selected script minimum and 15 maximum, and uses `ConfirmAction` whenever the proposal differs from the projection. Its summary explicitly says that changing configuration clears seats and assignments.

- [ ] **Step 3: Implement collapsed advanced settings**

Render the four Sentinel choices (`0`, `1`, `-1`, `2`) and all `fabled_pool` entries. Use pressed state plus text, expose role abilities as descriptions, and emit one mutation per click.

- [ ] **Step 4: Replace the read-only control placeholder**

`GameControlPanel` renders `LobbySetupPanel` only for `view.status === 'lobby'`; otherwise it retains the current read-only summary and complete-console link.

- [ ] **Step 5: Add compact left-panel styles**

Add form rows, segmented controls, inline warnings/errors, confirmation surface, and disabled/pending styles without changing the shell grid.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/storyteller frontend/src/styles/storyteller.css
git commit -m "feat: migrate storyteller lobby settings"
```

---

### Task 3: Build the Manual Assignment Draft Model

**Files:**
- Create: `frontend/src/composables/useManualAssignment.js`
- Create: `frontend/src/presentation/manualAssignment.js`

**Interfaces:**
- Consumes: storyteller projection fields `roles`, `composition`, `adjust_roles`, `seat_roles`, `bluffs`, `fake_pools`, `lunatic_minions`, `lunatic_bluffs`, `sentinel`, `script`, and `player_count`.
- Produces: draft refs/actions plus `manualAssignmentSummary(view, draft)` and `manualAssignmentPayload(draft)`.

- [ ] **Step 1: Implement pure role and composition helpers**

Export team order, expected-composition calculation (including script adjustments, Godfather choice, and Sentinel), duplicate detection, demon/minion hard-rule checks, bluff eligibility, and fake-role eligibility. Composition deviations outside the hard rules produce warnings only.

- [ ] **Step 2: Implement isolated draft ownership**

The composable exposes `active`, `assignments`, `bluffs`, `fakes`, `godfatherAdjustment`, `begin(view)`, `toggleRole(seat, roleId)`, fake/lunatic/bluff setters, `cancel()`, `invalidate()`, and `payload`. `begin` reconstructs compatible existing assignments from the projection.

- [ ] **Step 3: Invalidate incompatible drafts**

Watch server script, player count, and status. A changed configuration or non-lobby status clears the draft; connection loss does not erase it.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/composables/useManualAssignment.js frontend/src/presentation/manualAssignment.js
git commit -m "feat: model manual storyteller assignment"
```

---

### Task 4: Add Random Assignment and Forced Start

**Files:**
- Create: `frontend/src/components/storyteller/RoleAssignmentControls.vue`
- Create: `frontend/src/components/storyteller/StartControl.vue`
- Modify: `frontend/src/components/storyteller/LobbySetupPanel.vue`
- Modify: `frontend/src/styles/storyteller.css`

**Interfaces:**
- Consumes: `view.composition`, script name, player count, `view.can_start`, manual-mode state, connection state, and pending state.
- Produces: `begin-manual`, `assign-random`, and `start` intents.

- [ ] **Step 1: Add explicit random-assignment confirmation**

Render the current script, player count, and team composition inside `ConfirmAction`. Use `确认发牌并进入第一夜` as the second action label.

- [ ] **Step 2: Add forced-start explanation**

Show `StartControl` only when `view.can_start` is true and the game is still in the lobby. Explain that empty assigned seats remain available to late players.

- [ ] **Step 3: Connect lobby intent events**

Keep components command-free: `LobbySetupPanel` forwards intents upward and displays pending/error state supplied by `StorytellerLiveView`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/storyteller frontend/src/styles/storyteller.css
git commit -m "feat: add lobby assignment controls"
```

---

### Task 5: Add the Manual Role Assignment Interface

**Files:**
- Create: `frontend/src/components/storyteller/ManualAssignmentPanel.vue`
- Create: `frontend/src/components/storyteller/RolePicker.vue`
- Create: `frontend/src/components/storyteller/SpecialRoleFields.vue`
- Create: `frontend/src/components/storyteller/BluffPicker.vue`
- Modify: `frontend/src/components/storyteller/ContextPanel.vue`
- Modify: `frontend/src/components/storyteller/GrimoireBoard.vue`
- Modify: `frontend/src/components/storyteller/SeatNode.vue`
- Modify: `frontend/src/styles/storyteller.css`

**Interfaces:**
- Consumes: active manual draft, selected seat, roles, validation summary, and draft operations.
- Produces: `select-seat`, `toggle-role`, fake/lunatic/bluff mutations, `cancel-manual`, and `confirm-manual` intents.

- [ ] **Step 1: Preview draft assignments on the grimoire**

Pass `draftAssignments` into `GrimoireBoard`; each `SeatNode` resolves its displayed role from the draft first, then the server player/assigned role. Mark draft-modified seats textually and visually.

- [ ] **Step 2: Implement the grouped role picker**

Group roles by the four teams, show ability text, disable roles used by another seat, and toggle the selected seat's assignment without making a request.

- [ ] **Step 3: Implement global bluffs and special-role fields**

`BluffPicker` permits exactly three eligible absent good roles. `SpecialRoleFields` handles drunk/lunatic fake roles, at least one lunatic fake minion seat, exactly three lunatic bluffs, and Godfather outsider adjustment when applicable.

- [ ] **Step 4: Implement validation and confirmation**

Show assigned count, expected-versus-selected teams, warnings, and blocking errors. Disable confirmation until all seats and hard validations are complete. Emit the exact `{ assignments, bluffs, fakes }` payload.

- [ ] **Step 5: Prioritize manual context**

While manual mode is active, `ContextPanel` always renders `ManualAssignmentPanel`; closing it cancels the entire draft. Outside manual mode, preserve player-detail and join-panel priority.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/storyteller frontend/src/styles/storyteller.css
git commit -m "feat: migrate manual role assignment"
```

---

### Task 6: Wire Lobby Commands into the Live Preview

**Files:**
- Modify: `frontend/src/components/storyteller/StorytellerLiveView.vue`
- Modify: `frontend/src/components/storyteller/StorytellerHeader.vue`
- Modify: `frontend/src/components/storyteller/GameControlPanel.vue`
- Modify: `frontend/src/components/storyteller/ContextPanel.vue`
- Modify: `frontend/src/styles/storyteller.css`

**Interfaces:**
- Consumes: Tasks 1-5 service, command, components, and manual draft APIs.
- Produces: complete Vue lobby setup workflow with legacy escape for unmigrated live-game actions.

- [ ] **Step 1: Instantiate services once**

Create the storyteller service from the authenticated password, derive `connected` from `connectionStatus === 'connected'`, and route every child intent through `useStorytellerCommand`.

- [ ] **Step 2: Coordinate manual mode and selection**

Beginning manual mode selects the first incomplete seat when necessary. Successful manual submission cancels the draft after acknowledgement; server transitions and configuration changes invalidate it.

- [ ] **Step 3: Keep live-game behavior read-only**

When status becomes `playing`, render read-only setup summary and keep the header's `打开完整控制台` action. Do not expose any night/day mutation.

- [ ] **Step 4: Finish pending/error presentation**

Ensure disconnects disable writes without clearing the draft, errors remain local to the initiating section, and narrow drawers can still reach manual controls without covering the header.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/storyteller frontend/src/styles/storyteller.css
git commit -m "feat: enable Vue storyteller lobby workflow"
```

---

### Task 7: Add Consolidated Automated Coverage

**Files:**
- Create: `frontend/tests/storyteller-service.test.js`
- Create: `frontend/tests/storyteller-command.test.js`
- Create: `frontend/tests/storyteller-setup.test.js`
- Create: `frontend/tests/manual-assignment.test.js`
- Create: `frontend/tests/storyteller-lobby-flow.test.js`
- Modify: `frontend/tests/fixtures/storytellerView.js`

**Interfaces:**
- Consumes: completed Tasks 1-6.
- Produces: one consolidated regression suite for the entire migrated lobby slice.

- [ ] **Step 1: Add service and command tests**

Cover password headers, exact endpoint bodies, backend error propagation, pending cleanup, and disconnected write refusal.

- [ ] **Step 2: Add setup interaction tests**

Cover configuration confirmation and disarming, random assignment confirmation, fabled/Sentinel events, forced-start visibility, and read-only playing state.

- [ ] **Step 3: Add pure manual-model tests**

Cover draft reconstruction/invalidation, duplicate roles, exact demon/minion rules, warning-only composition differences, script adjustments, Sentinel, Godfather choice, bluff eligibility, drunk/lunatic fields, and exact payload shape.

- [ ] **Step 4: Add integrated lobby-flow tests**

Mount `StorytellerLiveView` with mocked projection and commands. Cover grimoire draft preview, selected-seat role editing, successful submit, server transition, reconnect disabling, fast projection-before-response, and formal legacy-route preservation.

- [ ] **Step 5: Run the complete frontend suite once**

Run: `npm --prefix frontend test`

Expected: all existing and newly consolidated frontend tests pass.

- [ ] **Step 6: Fix all consolidated failures and rerun the complete suite**

Make only evidence-driven fixes until the same complete command exits zero.

- [ ] **Step 7: Commit**

```bash
git add frontend/tests frontend/src
git commit -m "test: cover storyteller lobby migration"
```

---

### Task 8: Build, Document, and Verify End to End

**Files:**
- Modify: `README.md`
- Modify: `docs/migration/vue-vite-status.md`
- Modify: `frontend/dist/**`

**Interfaces:**
- Consumes: complete migrated lobby workflow and consolidated tests.
- Produces: committed production bundle, migration documentation, and acceptance evidence.

- [ ] **Step 1: Update migration documentation**

Document the migrated lobby capabilities, the still-read-only live-game boundary, the preview URL, and the complete-console escape.

- [ ] **Step 2: Run clean dependency, test, and build verification**

```bash
npm --prefix frontend ci
npm --prefix frontend test
npm --prefix frontend run build
```

- [ ] **Step 3: Run backend compatibility verification**

```bash
env PYTHONPATH=backend /Users/lichenxi/botc-grimoire/backend/.venv/bin/python -m unittest discover -s backend/tests -v
/Users/lichenxi/botc-grimoire/backend/.venv/bin/python -m compileall -q backend
env -u ALL_PROXY -u all_proxy -u HTTP_PROXY -u http_proxy -u HTTPS_PROXY -u https_proxy \
  NO_PROXY=localhost,127.0.0.1 no_proxy=localhost,127.0.0.1 \
  SMOKE_BASE=http://localhost:8001 \
  /Users/lichenxi/botc-grimoire/backend/.venv/bin/python backend/smoke_test.py
```

- [ ] **Step 4: Perform browser acceptance**

At `1366x768` and `1600x900`, exercise configuration confirmation, fabled/Sentinel controls, manual draft and cancel, manual submission, random confirmation, forced start, disconnect disabling, read-only playing transition, the legacy escape, and absence of document overflow or console errors. At 1100 px, verify both drawers and the complete manual workflow remain reachable below the fixed header.

- [ ] **Step 5: Commit documentation and bundle**

```bash
git add README.md docs/migration/vue-vite-status.md frontend/dist
git commit -m "docs: publish Vue storyteller lobby controls"
```

- [ ] **Step 6: Verify the final tree**

```bash
git diff --check
git status --short
```

Expected: no whitespace errors and an empty working tree.
