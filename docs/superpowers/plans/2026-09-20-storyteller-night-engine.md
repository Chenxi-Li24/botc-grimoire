# Storyteller Night Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the legacy night runner with a seat-centric, auditable night engine and a Vue storyteller workflow whose navigation stays fixed while task content scrolls.

**Architecture:** Move canonical game state out of player records, then layer an event/effect ledger, dynamic per-seat queue, outcome adjudication, information delivery, and complex handlers behind a focused night service. Expose one authoritative `night_workflow` projection through FastAPI/WebSocket and render it with isolated Vue components inside the existing three-column storyteller shell.

**Tech Stack:** Python 3 dataclasses and standard library, FastAPI/Pydantic, Vue 3 Composition API, Vite 8, native Fetch/WebSocket, Vitest 5, Vue Test Utils, unittest.

**Spec:** `docs/superpowers/specs/2026-09-20-storyteller-night-workflow-design.md`

## Global Constraints

- Stable English character IDs remain persistence keys; official Simplified Chinese is presentation data.
- A configured seat is the game entity even when no account has claimed it.
- The server is authoritative; the browser keeps only drafts and inspection state.
- First-night and other-night queues contain only in-play character instances plus applicable special steps.
- Backward navigation never mutates game state; explicit undo reverses an event and its dependency closure atomically.
- Lunatic acts before the real Demon and the Demon sees the Lunatic target.
- A kill choice is pending until storyteller adjudication; secret death affects later eligibility before dawn publication.
- Deterministic unique information is auto-sent and reported; ambiguous or impaired information pauses for adjudication.
- Status effects retain source, lifetime, transitions, and history.
- Long task descriptions scroll only the task body; Previous, progress, and Next/Dawn remain fixed.
- Incomplete required work warns but never traps the storyteller; forced continuation is explicit and journaled.
- Per the user's direction, migration code is completed before tests are added or run; verification is one consolidated final task.

## Review Focus

- A claimed player disconnecting or leaving must not remove the seat's character, life, effects, or pending actions; pinned by `test_unclaimed_seat_survives_player_removal` in Task 12.
- A secretly dead seat whose ordinary step is later in the queue must be skipped while a matching death trigger is inserted; pinned by `test_secret_death_rebuilds_unexecuted_suffix` in Task 12.
- Undoing Pit-Hag after derived information/effects/messages exist must either reverse the full closure or do nothing; pinned by `test_pithag_undo_is_atomic` in Task 12.
- Poisoner/Widow effects must suspend during temporary source incapacity and follow distinct terminal lifetimes; pinned by `test_effect_lifetimes_suspend_resume_and_end` in Task 12.
- A long instruction, warning appearance, and Next-to-Dawn label change must not move either navigation target; pinned by `night-task-panel.test.js` in Task 12.

---

### Task 1: Normalize Character, Script, Night-Order, and Locale Data

**Files:**
- Create: `backend/app/catalog/__init__.py`
- Create: `backend/app/catalog/models.py`
- Create: `backend/app/catalog/compiler.py`
- Create: `backend/app/catalog/zh_cn.py`
- Modify: `backend/app/roles.py`
- Modify: `backend/app/scripts/__init__.py`
- Modify: `backend/app/night_order.py`

**Interfaces:**
- Consumes: existing script `ROLES`, generated `NIGHT_ORDER`, and `NIGHT_ACTIONS` dictionaries.
- Produces: `CharacterSpec`, `ScriptPack`, `NightTiming`, `SelectionSpec`, `compile_builtin_packs() -> dict[str, ScriptPack]`, and `pack_to_view(pack) -> dict`.

- [ ] **Step 1: Define the normalized immutable contract**

```python
@dataclass(frozen=True)
class NightTiming:
    first: int | None = None
    other: int | None = None
    trigger: str = "normal"

@dataclass(frozen=True)
class CharacterSpec:
    id: str
    team: str
    name_key: str
    ability_key: str
    night: NightTiming
    selection: SelectionSpec | None = None
    information_resolver: str | None = None
    complex_handler: str | None = None

@dataclass(frozen=True)
class ScriptPack:
    id: str
    min_players: int
    characters: tuple[CharacterSpec, ...]
    locale: Mapping[str, str]
```

- [ ] **Step 2: Compile current built-ins without source-specific runtime branching**

`compile_builtin_packs()` validates unique character IDs, valid timing values, known teams, and referenced resolver/handler keys. Unsupported custom characters compile as `complex_handler="manual"`, retaining imported ability/reminder text.

- [ ] **Step 3: Separate official Chinese labels from stable IDs**

Populate the official three editions with `暗流涌动`, `黯月初升`, `梦殒春宵` and the confirmed official character labels. Keep community overrides inside their pack locale and remove label-based logic.

- [ ] **Step 4: Point compatibility exports at compiled packs**

Keep `SCRIPTS`, `SCRIPT_ADJUST_ROLES`, and old view dictionaries available as derived adapters so lobby code continues working while the night engine consumes `ScriptPack` directly.

- [ ] **Step 5: Commit**

```bash
git add backend/app/catalog backend/app/roles.py backend/app/scripts/__init__.py backend/app/night_order.py
git commit -m "refactor: normalize character runtime data"
```

---

### Task 2: Make Seats the Canonical Game Entities

**Files:**
- Create: `backend/app/state.py`
- Create: `backend/app/save_codec.py`
- Modify: `backend/app/game.py`

**Interfaces:**
- Consumes: `ScriptPack` and legacy save dictionaries.
- Produces: `SeatState`, `GameState`, `decode_save(payload, pack) -> GameState`, `encode_save(state) -> dict`, and `GameManager.seat_state(seat) -> SeatState`.

- [ ] **Step 1: Define canonical seat and account state**

```python
@dataclass
class SeatState:
    seat: int
    claimed_by: str | None = None
    character_id: str | None = None
    perceived_character_id: str | None = None
    alignment: str = "good"
    alive: bool = True
    public_alive: bool = True
    died_at: str | None = None
    effect_ids: list[str] = field(default_factory=list)
    ability_state: dict[str, dict] = field(default_factory=dict)

@dataclass
class PlayerAccount:
    id: str
    name: str
    seat: int | None = None
    wish: str | None = None
```

- [ ] **Step 2: Add versioned save migration**

Decode unversioned saves by folding `Player.role_id`, player life fields, `seat_roles`, `seat_alive`, fakes, role/team changes, and markers into `SeatState`. Write `schema_version: 2`; preserve the original save until the new payload serializes and validates.

- [ ] **Step 3: Route game operations through seats**

Replace role/life ownership in assignment, join/leave, nomination, vote, player view, storyteller view, and review builders. `remove_player()` clears only the claim, while `reset()` or explicit game configuration clears seats.

- [ ] **Step 4: Keep transition adapters read-only**

Expose legacy `seat_roles`, `seat_alive`, and player role fields only in view/save compatibility adapters; mutation methods write canonical seats exactly once.

- [ ] **Step 5: Commit**

```bash
git add backend/app/state.py backend/app/save_codec.py backend/app/game.py
git commit -m "refactor: make seats canonical game state"
```

---

### Task 3: Add an Event Journal and Sourced Effect Ledger

**Files:**
- Create: `backend/app/night/__init__.py`
- Create: `backend/app/night/models.py`
- Create: `backend/app/night/journal.py`
- Create: `backend/app/night/effects.py`
- Modify: `backend/app/state.py`
- Modify: `backend/app/game.py`

**Interfaces:**
- Consumes: canonical `GameState`.
- Produces: `EventRecord`, `EffectRecord`, `EventJournal.append()`, `EventJournal.undo()`, `EffectLedger.apply()`, `EffectLedger.transition()`, and `EffectLedger.advance(trigger)`.

- [ ] **Step 1: Define durable events, transactions, and effects**

```python
@dataclass
class EventRecord:
    id: str
    kind: str
    payload: dict
    inverse: dict
    depends_on: list[str]
    transaction_id: str
    state: str = "active"

@dataclass
class EffectRecord:
    id: str
    type: str
    target_seat: int
    source_seat: int | None
    source_character: str | None
    source_event: str
    payload: dict
    lifetime_policy: dict
    state: str
    transitions: list[dict]
```

- [ ] **Step 2: Implement atomic dependency-aware undo**

`journal.undo(event_id)` computes every active descendant, returns a preview when `confirm=False`, and on confirmation applies inverses in reverse topological order inside a cloned state. Commit the clone only when every inverse succeeds; message events append retractions rather than deleting history.

- [ ] **Step 3: Implement semantic effect advancement**

Support `until_dusk`, `until_next_choice`, `while_source_has_ability`, `round_count`, `game_long`, and `manual`. Temporary source incapacity creates `suspended` and `resumed` transitions; expiry/permanent source loss creates `ended`.

- [ ] **Step 4: Migrate markers into effect views**

Legacy marker mutations create manual effects with a migration source. Storyteller and information projections return both compact active badges and expandable histories.

- [ ] **Step 5: Commit**

```bash
git add backend/app/night backend/app/state.py backend/app/game.py
git commit -m "feat: add night event and effect ledgers"
```

---

### Task 4: Build the Dynamic Per-Seat Night Queue

**Files:**
- Create: `backend/app/night/queue.py`
- Create: `backend/app/night/service.py`
- Modify: `backend/app/game.py`

**Interfaces:**
- Consumes: `GameState`, `ScriptPack`, `EventJournal`, and `EffectLedger`.
- Produces: `NightStep`, `NightQueue.build()`, `NightQueue.rebuild_suffix()`, and `NightService.navigate(step_id | direction, force=False)`.

- [ ] **Step 1: Define action instances instead of character keys**

```python
@dataclass
class NightStep:
    id: str
    actor_seat: int | None
    character_id: str
    perceived_as: str | None
    trigger: str
    order: int
    status: str = "upcoming"
    skip_reason: str | None = None
    required_fields: tuple[str, ...] = ()
```

- [ ] **Step 2: Generate first/other-night queues from in-play seats**

Build one step per seat/ability instance, include conditional in-play steps with skip reasons, omit absent characters, include unclaimed assigned seats, and order Lunatic before real Demon. Drunk uses the perceived character's timing.

- [ ] **Step 3: Rebuild only the unexecuted suffix**

When life, character, alignment, effects, or triggers change, preserve completed/undone history and stable IDs, then regenerate future steps. A secretly dead actor gets an ordinary skip; qualifying death-trigger steps are inserted with source metadata.

- [ ] **Step 4: Separate navigation from execution**

Previous/goto changes only `current_step_id`. Next validates `required_fields`; the first blocked attempt returns structured omissions and a force token, while a confirmed force writes a `forced_skip` journal event.

- [ ] **Step 5: Commit**

```bash
git add backend/app/night/queue.py backend/app/night/service.py backend/app/game.py
git commit -m "feat: add dynamic seat night queue"
```

---

### Task 5: Add Pending Outcome and Confidential Death Adjudication

**Files:**
- Create: `backend/app/night/outcomes.py`
- Modify: `backend/app/night/models.py`
- Modify: `backend/app/night/service.py`
- Modify: `backend/app/game.py`

**Interfaces:**
- Consumes: action selections, active effects, queue, and journal.
- Produces: `PendingOutcome`, `OutcomeAdjudicator.create()`, `OutcomeAdjudicator.resolve()`, and `OutcomeAdjudicator.publish_dawn()`.

- [ ] **Step 1: Model choice separately from outcome**

```python
@dataclass
class PendingOutcome:
    id: str
    source_event: str
    source_seat: int | None
    source_character: str
    selected_seats: list[int]
    hints: list[dict]
    resolution: str | None = None
    affected_seats: list[int] = field(default_factory=list)
```

Supported resolutions are `secret_death`, `no_death`, `delayed`, `redirected`, `transformation`, and `choice_only`.

- [ ] **Step 2: Provide rule hints without auto-overruling the storyteller**

Collect protection, source incapacity, already-dead target, replacement, and special-character hints. Resolution always requires an explicit storyteller decision when a death is possible.

- [ ] **Step 3: Apply secret death immediately to night eligibility**

Set `alive=False`, retain `public_alive=True`, record source seat/character/ability, `is_demon_attack`, `arbitrary`, prevented/replaced links, and rebuild the queue suffix. Insert Ravenkeeper-style triggers for night death and Sage-style triggers only for a recorded Demon attack.

- [ ] **Step 4: Implement Lunatic-to-Demon disclosure and dawn publication**

Lunatic selection resolves as `choice_only`; the real Demon task receives that target in its context. `publish_dawn()` flips public life state, ends dusk-bound effects, and emits the public death list without exposing hidden rationale.

- [ ] **Step 5: Commit**

```bash
git add backend/app/night/outcomes.py backend/app/night/models.py backend/app/night/service.py backend/app/game.py
git commit -m "feat: adjudicate confidential night outcomes"
```

---

### Task 6: Add Structured Information and Persistent Ability State

**Files:**
- Create: `backend/app/night/information.py`
- Create: `backend/app/night/resolvers.py`
- Create: `backend/app/night/ability_state.py`
- Modify: `backend/app/night/service.py`
- Modify: `backend/app/game.py`

**Interfaces:**
- Consumes: facts, targets, registration choices, active-effect snapshot, and character resolver key.
- Produces: `InformationDraft`, `InformationDelivery`, `InformationEngine.prepare()`, `InformationEngine.deliver()`, and character-keyed ability-state helpers.

- [ ] **Step 1: Implement the information pipeline**

```python
@dataclass
class InformationClaim:
    label: str
    value: object
    truthful: bool

@dataclass
class InformationDelivery:
    id: str
    actor_seat: int
    real_character: str
    perceived_character: str
    targets: list[int]
    true_result: object
    delivered_result: object
    claims: list[InformationClaim]
    registrations: list[dict]
    effect_snapshot: list[str]
    reason: str | None
```

- [ ] **Step 2: Auto-deliver only one unambiguous legal result**

If the resolver yields one result and there is no impairment, registration choice, discretion, or unknown handler, append delivery plus a non-blocking storyteller notice. Otherwise return an adjudication draft requiring explicit claims and correctness.

- [ ] **Step 3: Implement Drunk, poison, Vortox, Spy/Recluse, and Dreamer records**

Drunk acts as perceived role and may receive true or false information. Dreamer stores target plus one good and one evil displayed character, with independent truth flags. Review correction appends a correction event instead of rewriting delivery history.

- [ ] **Step 4: Store cross-phase ability state**

Add typed helpers for Fortune Teller red herring, Grandmother grandchild, Balloonist history, Philosopher/Cannibal acquired abilities, Juggler guesses, once-per-game usage, Fang Gu jump, Po charge, Shabaloth/Pukka targets, and Chambermaid wake events.

- [ ] **Step 5: Commit**

```bash
git add backend/app/night/information.py backend/app/night/resolvers.py backend/app/night/ability_state.py backend/app/night/service.py backend/app/game.py
git commit -m "feat: structure night information delivery"
```

---

### Task 7: Implement Pit-Hag and Timed Status Handlers

**Files:**
- Create: `backend/app/night/handlers/__init__.py`
- Create: `backend/app/night/handlers/pit_hag.py`
- Create: `backend/app/night/handlers/status_roles.py`
- Modify: `backend/app/night/service.py`
- Modify: `backend/app/game.py`

**Interfaces:**
- Consumes: `NightService`, journal transactions, queue positions, and normalized character capabilities.
- Produces: `PitHagHandler.preview()`, `PitHagHandler.confirm()`, `apply_poisoner()`, `apply_widow()`, and `apply_cerenovus()`.

- [ ] **Step 1: Make Pit-Hag submission a pending card**

The preview reports target, old/new character, current alignment, in-play conflict, relative order, future-step changes, immediate start-knowing information, and Demon-creation consequences. No state changes before confirmation.

- [ ] **Step 2: Apply transformation as one transaction**

An in-play character including a dead instance creates a storyteller-only silent-failure event. Success changes character but preserves alignment, reevaluates old/new effects, inserts start-knowing immediately, inserts a later normal action at standard order, and defers already-passed timing to the next night.

- [ ] **Step 3: Apply created-Demon restrictions**

Mark all deaths that night storyteller-arbitrary, suppress the created Demon's ordinary choose-to-kill action, activate passive/non-kill ability parts, and attribute arbitrary deaths to Pit-Hag so Demon-kill-only triggers remain false.

- [ ] **Step 4: Implement precise status lifetimes**

Poisoner lasts through next day to dusk and suspends on temporary source incapacity. Widow lasts while Widow has ability, ends on death/permanent role loss, and suspends/resumes. Cerenovus records claimed character, start event, replacement, expiry, and history.

- [ ] **Step 5: Commit**

```bash
git add backend/app/night/handlers backend/app/night/service.py backend/app/game.py
git commit -m "feat: implement pit hag and timed effects"
```

---

### Task 8: Expose a Modular Night API and Authoritative Projection

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/night.py`
- Create: `backend/app/api/schemas.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/game.py`

**Interfaces:**
- Consumes: `NightService` commands and `GameManager.storyteller_view()`.
- Produces: `/api/night/step`, `/api/night/select`, `/api/night/outcome`, `/api/night/information`, `/api/night/effect`, `/api/night/pit-hag`, `/api/night/undo`, and `night_workflow` projection.

- [ ] **Step 1: Define explicit command schemas**

```python
class NavigateBody(BaseModel):
    direction: Literal["previous", "next", "goto"]
    step_id: str | None = None
    force_token: str | None = None

class ResolveOutcomeBody(BaseModel):
    outcome_id: str
    resolution: Literal["secret_death", "no_death", "delayed", "redirected", "transformation", "choice_only"]
    affected_seats: list[int] = []
    rationale: str = ""
```

- [ ] **Step 2: Return domain errors without partial mutation**

Map stale IDs, missing adjudication, invalid targets, expired force tokens, and undo conflicts to HTTP 409 with `{code, message, details}`. Authentication remains the existing storyteller header.

- [ ] **Step 3: Build privacy-filtered views**

`night_workflow` includes queue, current task, current/ended effects, notices, pending outcome/information cards, undo previews, and seat context for storytellers. Player views receive only their own prompt/delivery and never truth, hidden effects, secret death, or rationale.

Record server acceptance for every private delivery and WebSocket delivery when observable. Player acknowledgement is optional telemetry and never blocks queue progression.

- [ ] **Step 4: Keep legacy endpoints as adapters during cutover**

Old endpoints call the new service where semantics match and return a deprecation field; remove direct mutation paths so WebSocket broadcasts always project one state.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api backend/app/main.py backend/app/game.py
git commit -m "feat: expose storyteller night workflow api"
```

---

### Task 9: Add Vue Night State, Commands, and Presentation Helpers

**Files:**
- Create: `frontend/src/composables/useNightWorkflow.js`
- Create: `frontend/src/presentation/nightWorkflow.js`
- Modify: `frontend/src/services/storyteller.js`
- Modify: `frontend/src/components/storyteller/StorytellerLiveView.vue`

**Interfaces:**
- Consumes: `view.night_workflow`, existing command runner, and Task 8 endpoints.
- Produces: selected step/seat drafts, stable pending keys, `currentTask`, `orderedSteps`, and all night command methods.

- [ ] **Step 1: Add authenticated command methods**

```js
navigate: (payload) => command('/api/night/step', payload),
selectNightTargets: (payload) => command('/api/night/select', payload),
resolveOutcome: (payload) => command('/api/night/outcome', payload),
deliverInformation: (payload) => command('/api/night/information', payload),
confirmPitHag: (payload) => command('/api/night/pit-hag', payload),
undoNightEvent: (payload) => command('/api/night/undo', payload),
```

- [ ] **Step 2: Keep drafts local and projection authoritative**

`useNightWorkflow` stores selected targets, selected character, information claims, outcome choice, inspected step, and force token. A new server projection clears only drafts whose source step/event completed or disappeared; reconnect keeps valid inspection and target drafts.

- [ ] **Step 3: Centralize labels and task summaries**

Presentation helpers map status, trigger, outcome, effect transition, and validation codes to Chinese labels without embedding game rules in Vue components.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/composables/useNightWorkflow.js frontend/src/presentation/nightWorkflow.js frontend/src/services/storyteller.js frontend/src/components/storyteller/StorytellerLiveView.vue
git commit -m "feat: add vue night workflow state"
```

---

### Task 10: Build the Fixed-Navigation Night Workspace

**Files:**
- Create: `frontend/src/components/storyteller/night/NightStepList.vue`
- Create: `frontend/src/components/storyteller/night/NightTaskPanel.vue`
- Create: `frontend/src/components/storyteller/night/NightNavigation.vue`
- Create: `frontend/src/components/storyteller/night/SeatTargetPicker.vue`
- Create: `frontend/src/components/storyteller/night/OutcomeAdjudicator.vue`
- Create: `frontend/src/components/storyteller/night/InformationEditor.vue`
- Create: `frontend/src/components/storyteller/night/EffectHistory.vue`
- Create: `frontend/src/components/storyteller/night/PitHagCard.vue`
- Create: `frontend/src/components/storyteller/night/UndoPreview.vue`
- Modify: `frontend/src/components/storyteller/GameControlPanel.vue`
- Modify: `frontend/src/components/storyteller/ContextPanel.vue`
- Modify: `frontend/src/components/storyteller/GrimoireBoard.vue`
- Modify: `frontend/src/components/storyteller/SeatNode.vue`
- Modify: `frontend/src/styles/storyteller.css`

**Interfaces:**
- Consumes: Task 9 workflow state/actions and storyteller projection.
- Produces: complete first/other-night desktop and drawer UI.

- [ ] **Step 1: Render only relevant per-seat action instances**

The left list shows completed/current/skipped/undone/upcoming states, seat/character identity, and skip reason. Clicking inspects a step without executing or undoing anything.

- [ ] **Step 2: Render task-specific middle content**

The task body switches among target selection, outcome adjudication, structured information, Pit-Hag preview, effect history, automatic-send notice, manual-only reminder, and undo preview. Empty/unclaimed seats remain selectable and are labeled `线下/未领取`.

- [ ] **Step 3: Fix navigation independently of description length**

```css
.night-task-panel {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) 44px 64px;
}
.night-task-body { overflow: auto; min-height: 0; }
.night-task-warning { overflow: auto; }
.night-navigation {
  display: grid;
  grid-template-columns: 112px minmax(0, 1fr) 112px;
  align-items: center;
  padding-bottom: env(safe-area-inset-bottom);
}
```

Previous is always left, progress is centered, and Next/Dawn is always right. The warning row stays reserved even when empty; only `.night-task-body` scrolls.

- [ ] **Step 4: Add explicit force and undo interactions**

The first incomplete Next click renders exact omissions in the reserved row and changes only the right action to `仍然继续`. Undo always opens a dependency preview and never shares behavior with Previous.

- [ ] **Step 5: Add board context without exposing hidden state publicly**

Show acting, selected, drafted, secret-dead, and active-effect states in the storyteller board. Seat detail expands effect provenance/history and offers return to current task while fixed navigation remains visible.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/storyteller/night frontend/src/components/storyteller frontend/src/styles/storyteller.css
git commit -m "feat: build fixed storyteller night workspace"
```

---

### Task 11: Complete the Vue Cutover and Remove Night Mutations from Legacy

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/services/navigation.js`
- Create: `frontend/src/pages/StorytellerPage.vue`
- Delete: `frontend/src/pages/StorytellerPreviewPage.vue`
- Modify: `frontend/src/components/storyteller/StorytellerHeader.vue`
- Modify: `frontend/src/components/storyteller/StorytellerLiveView.vue`
- Modify: `frontend/legacy/app.js`
- Modify: `docs/migration/vue-vite-status.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: Tasks 1-10.
- Produces: `/#/storyteller` as the primary Vue storyteller route with a read-only legacy escape for unmigrated day/review tools.

- [ ] **Step 1: Promote the Vue route**

Route `/#/storyteller` to `StorytellerPreviewPage` (rename the component to `StorytellerPage.vue`) and redirect `/#/storyteller-preview` to the canonical hash route. Preserve password/session keys.

- [ ] **Step 2: Make legacy night controls read-only**

Disable or remove legacy night next/previous, kill, transform, reply, and marker mutation handlers; link to the Vue storyteller route so two clients cannot write conflicting semantics.

- [ ] **Step 3: Preserve day/review access during later migration**

Expose a clearly labeled `旧版白天与复盘工具` link only for functionality outside this slice. The Vue header no longer calls the legacy page the complete console.

- [ ] **Step 4: Document schema and operational changes**

Record save schema v2, automatic legacy-save migration, night API paths, official locale source, current migration boundary, and recovery procedure.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.vue frontend/src/services/navigation.js frontend/src/components/storyteller frontend/legacy/app.js docs/migration/vue-vite-status.md README.md
git commit -m "feat: promote vue storyteller night workflow"
```

---

### Task 12: Add and Run Consolidated Verification

**Files:**
- Create: `backend/tests/night_helpers.py`
- Create: `backend/tests/test_save_codec.py`
- Create: `backend/tests/test_night_queue.py`
- Create: `backend/tests/test_night_outcomes.py`
- Create: `backend/tests/test_night_information.py`
- Create: `backend/tests/test_night_effects.py`
- Create: `backend/tests/test_pit_hag.py`
- Create: `backend/tests/test_night_api.py`
- Create: `frontend/tests/night-workflow.test.js`
- Create: `frontend/tests/night-task-panel.test.js`
- Create: `frontend/tests/night-adjudication.test.js`
- Modify: `backend/smoke_test.py`
- Modify: `frontend/tests/app-routing.test.js`

**Interfaces:**
- Consumes: completed migration.
- Produces: regression coverage and one verified production build.

- [ ] **Step 1: Add backend contract and regression tests**

Cover legacy save migration, unclaimed seats, first/other-night ordering, Lunatic target disclosure, secret death queue changes, death-source triggers, effect lifetime transitions, deterministic/impaired information, Dreamer claims, Pit-Hag timing/created-Demon/silent-failure/alignment/undo, forced continuation, and privacy filtering.

Pin the review-focus cases with these exact assertions, using `make_game()` to create an isolated `GameManager` with autosave disabled:

```python
def test_unclaimed_seat_survives_player_removal():
    game, player_id = make_game({1: "washerwoman", 2: "imp"}, claim_seat=1)
    game.remove_player(player_id)
    assert game.seat_state(1).character_id == "washerwoman"
    assert game.seat_state(1).claimed_by is None

def test_secret_death_rebuilds_unexecuted_suffix():
    game, _ = make_game({1: "imp", 2: "ravenkeeper", 3: "undertaker"}, night=2)
    outcome = game.night.resolve_test_attack(source=1, target=2, resolution="secret_death")
    assert game.seat_state(2).public_alive is True
    assert game.night.queue.step_for(3, "undertaker").status == "upcoming"
    assert game.night.queue.step_for(2, "ravenkeeper", trigger="death").depends_on == [outcome.event_id]

def test_pithag_undo_is_atomic():
    game, _ = make_game({1: "pithag", 2: "clockmaker", 3: "fanggu"}, night=2)
    event = game.night.confirm_pit_hag(actor=1, target=2, character="noble")
    delivery = game.night.deliver_test_information(actor=2, depends_on=[event.id])
    preview = game.night.undo(event.id, confirm=False)
    assert set(preview.event_ids) == {event.id, delivery.event_id}
    before = game.save_payload()
    game.night.inject_inverse_failure(delivery.event_id)
    try:
        game.night.undo(event.id, confirm=True)
    except UndoConflict:
        pass
    else:
        raise AssertionError("undo must reject an incomplete dependency rollback")
    assert game.save_payload() == before

def test_effect_lifetimes_suspend_resume_and_end():
    game, _ = make_game({1: "poisoner", 2: "widow", 3: "chef"}, night=2)
    poison = game.night.apply_poisoner(source=1, target=3)
    widow = game.night.apply_widow(source=2, target=3)
    game.night.set_source_ability(1, active=False, permanent=False)
    game.night.set_source_ability(2, active=False, permanent=False)
    assert [game.effects.get(x).state for x in (poison.id, widow.id)] == ["suspended", "suspended"]
    game.night.set_source_ability(1, active=True, permanent=False)
    game.night.set_source_ability(2, active=True, permanent=False)
    assert [game.effects.get(x).state for x in (poison.id, widow.id)] == ["active", "active"]
    game.effects.advance("dusk")
    assert game.effects.get(poison.id).state == "ended"
    assert game.effects.get(widow.id).state == "active"
```

- [ ] **Step 2: Add Vue workflow and layout tests**

Mount short and long tasks with warnings absent/present and labels `下一步`/`天亮`; assert the same grid rows and `112px` navigation slots, scrollable body, fixed bar, force arming, undo preview, disconnected writes, projection refresh, and unclaimed-seat operation.

```js
it.each([
  ['短提示', '', '下一步'],
  ['很长的角色提示'.repeat(120), '还有 1 项必填操作未完成', '仍然继续'],
  ['黎明结算', '', '天亮'],
])('keeps navigation slots fixed for variable content', async (description, warning, nextLabel) => {
  const wrapper = mount(NightTaskPanel, {
    props: { task: taskFixture({ description }), warning, nextLabel },
  })
  expect(wrapper.get('[data-night-task]').classes()).toContain('night-task-panel')
  expect(getComputedStyle(wrapper.get('[data-night-navigation]').element).gridTemplateColumns)
    .toBe('112px minmax(0px, 1fr) 112px')
  expect(wrapper.get('[data-night-previous]').attributes('data-slot')).toBe('left')
  expect(wrapper.get('[data-night-next]').attributes('data-slot')).toBe('right')
})
```

- [ ] **Step 3: Run Python checks**

```bash
python -m unittest discover -s backend/tests -v
python -m compileall backend/app backend/tools backend/smoke_test.py
python backend/smoke_test.py
```

Expected: every test passes, compileall reports no syntax errors, and smoke output ends successfully.

- [ ] **Step 4: Run frontend checks and production build**

```bash
npm --prefix frontend test
npm --prefix frontend run build
```

Expected: Vitest reports all files passing and Vite writes `frontend/dist` without errors.

- [ ] **Step 5: Run browser acceptance at desktop and drawer widths**

Start the test server, open `/#/storyteller`, exercise first-night navigation, Lunatic/Demon decisions, forced continuation, secret death, automatic/adjudicated information, effect history, Pit-Hag preview/undo, and dawn. Confirm navigation targets do not move at 1366×768 or a narrow drawer viewport.

- [ ] **Step 6: Commit**

```bash
git add backend/tests backend/smoke_test.py frontend/tests frontend/dist
git commit -m "test: verify storyteller night migration"
```
