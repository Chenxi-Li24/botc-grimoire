# Vue Storyteller Day Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the complete daytime talk, nomination, voting, resolution, and end-day workflow inside the existing Vue storyteller grimoire.

**Architecture:** Extend the existing storyteller service and command wrapper, reuse the player plan's pure participant/nomination presentation helpers, and add focused components under `frontend/src/components/storyteller/day/`. The existing FastAPI endpoints and storyteller WebSocket projection remain authoritative.

**Tech Stack:** Vue 3, Vite 8, Vitest 5, `@vue/test-utils`, existing FastAPI REST/WebSocket API.

**Spec:** `docs/superpowers/specs/2026-09-20-player-day-vue-migration-design.md`

## Global Constraints

- Existing REST endpoints, WebSocket projections, local-storage identity, and the JSON save format remain compatible.
- The server is authoritative; the client stores only temporary participant selections and confirmation state.
- No new frontend runtime dependency is added.
- The grimoire remains the central desktop object and selected seats remain usable during the daytime workflow.
- Storyteller traveler administration, chat supervision, winner declaration, review editing, room/reset/load, and arbitrary marker controls remain explicit legacy escapes.
- Controls must remain stable as nomination history and instructional copy change length.

## Review Focus

- A traveler string ID is selected as nominator or nominee: Task 2 tests that it remains a string through the service call.
- A player submits or retracts a vote while the storyteller panel is open: Task 3 tests projection-driven rendering without losing the selected nomination draft.
- An unresolved nomination exists when ending the day: Task 3 tests that the API error is displayed and the confirmation resets safely.
- A dead participant has already spent their dead vote: Task 3 tests that the vote control is disabled while living and unused-dead-vote controls remain active.
- Day content grows beyond one desktop viewport: Task 4 browser acceptance checks sticky controls and absence of horizontal document overflow.

---

### Task 1: Extend storyteller day command and presentation services

**Files:**
- Modify: `frontend/src/services/storyteller.js`
- Modify: `frontend/src/presentation/player.js`
- Create: `frontend/src/presentation/dayWorkflow.js`
- Modify: `frontend/tests/fixtures/storytellerView.js`
- Modify: `frontend/tests/storyteller-service.test.js`
- Create: `frontend/tests/day-workflow-presentation.test.js`

**Interfaces:**
- Consumes: player-plan helpers `participantLabel(id, seats, travelers)` and `groupNominations(nominations)`.
- Produces: storyteller methods `setDayStage(stage)`, `startNomination(nominator, nominee)`, `toggleVote(participant)`, `resolveNomination(passed)`, and `endDay()`; pure `dayParticipants(view)`, `canVote(participant, view)`, `currentVoteSummary(view)`, `executionStanding(view)`, and the shared `groupDeaths(view.deaths)` output.

- [ ] **Step 1: Write failing service and presentation tests**

```js
it('keeps traveler ids when starting a nomination', async () => {
  const service = createStorytellerService('secret')
  await service.startNomination(2, 't1')
  expect(fetch).toHaveBeenCalledWith('/api/nomination', expect.objectContaining({
    method: 'POST', body: JSON.stringify({ nominator: 2, nominee: 't1' }),
  }))
})

it('computes the current threshold and leading execution without mutating view', () => {
  const view = makeStorytellerDayView()
  const frozen = structuredClone(view)
  expect(currentVoteSummary(view)).toEqual({ votes: 2, quorum: 3, passes: false })
  expect(view).toEqual(frozen)
})
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `cd frontend && npm test -- tests/storyteller-service.test.js tests/day-workflow-presentation.test.js`

Expected: FAIL because day methods and presentation helpers do not exist.

- [ ] **Step 3: Implement exact service mappings and helpers**

```js
setDayStage: (stage) => command('/api/day/stage', { stage }),
startNomination: (nominator, nominee) => command('/api/nomination', { nominator, nominee }),
toggleVote: (seat) => command('/api/nomination/vote', { seat }),
resolveNomination: (passed) => command('/api/nomination/resolve', { passed }),
endDay: () => command('/api/day/end'),
```

`dayParticipants` returns assigned seats plus public travelers with stable `number | string` IDs. `canVote` checks alive state and unused dead-vote state. `executionStanding` considers only passed numeric-seat nominations for the current day and reports a unique leader or a tie.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `cd frontend && npm test -- tests/storyteller-service.test.js tests/day-workflow-presentation.test.js tests/player-presentation.test.js`

Expected: PASS for endpoint payloads, participant types, thresholds, ties, and immutability.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/services/storyteller.js frontend/src/presentation/player.js frontend/src/presentation/dayWorkflow.js frontend/tests/fixtures/storytellerView.js frontend/tests/storyteller-service.test.js frontend/tests/day-workflow-presentation.test.js
git commit -m "feat: add storyteller day command layer"
```

### Task 2: Add daytime stage and nomination composition

**Files:**
- Create: `frontend/src/components/storyteller/day/DayControlPanel.vue`
- Create: `frontend/src/components/storyteller/day/NominationComposer.vue`
- Create: `frontend/tests/storyteller-day-composer.test.js`

**Interfaces:**
- Consumes: Task 1 `dayParticipants`; props `view`, `connected`, `pending`, `error`.
- Produces: events `set-stage(stage)` and `start-nomination({ nominator, nominee })`; local draft `{ nominator: number | string | null, nominee: number | string | null }`.

- [ ] **Step 1: Write failing stage and composition tests**

```js
it('switches from talk to nomination stage', async () => {
  const wrapper = mount(DayControlPanel, { props: { view: makeStorytellerDayView({ day_stage: 'talk' }), connected: true } })
  await wrapper.get('[data-day-stage="nom"]').trigger('click')
  expect(wrapper.emitted('set-stage')).toEqual([['nom']])
})

it('submits a numeric nominator and traveler nominee only after confirmation', async () => {
  const wrapper = mount(NominationComposer, { props: { view: makeStorytellerDayView(), connected: true } })
  await wrapper.get('[data-nominator="2"]').trigger('click')
  await wrapper.get('[data-nominee="t1"]').trigger('click')
  await wrapper.get('[data-confirm-nomination]').trigger('click')
  expect(wrapper.emitted('start-nomination')).toEqual([[{ nominator: 2, nominee: 't1' }]])
})
```

Cover same-participant rejection, dead nominator exclusion, already-nominated-today exclusion, traveler exclusion after exile, disconnection disabling, and server error display without losing the draft.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `cd frontend && npm test -- tests/storyteller-day-composer.test.js`

Expected: FAIL because the day components do not exist.

- [ ] **Step 3: Implement stage controls and the two-column participant composer**

```vue
<NominationComposer
  v-if="view.day_stage === 'nom' && !view.current"
  :view="view"
  :connected="connected"
  :busy="pending.includes('day:nomination')"
  :error="error"
  @start-nomination="$emit('start-nomination', $event)"
/>
```

The composer keeps participant IDs uncoerced, uses buttons for every participant, labels travelers distinctly, and resets only after the parent reports a successful command.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `cd frontend && npm test -- tests/storyteller-day-composer.test.js tests/day-workflow-presentation.test.js`

Expected: PASS for stage changes, eligibility, mixed IDs, confirmation and retained errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/storyteller/day/DayControlPanel.vue frontend/src/components/storyteller/day/NominationComposer.vue frontend/tests/storyteller-day-composer.test.js
git commit -m "feat: add storyteller nomination composer"
```

### Task 3: Add live voting, resolution, history, and end-day controls

**Files:**
- Create: `frontend/src/components/storyteller/day/VoteBoard.vue`
- Create: `frontend/src/components/storyteller/day/NominationHistory.vue`
- Create: `frontend/src/components/storyteller/day/DayResolution.vue`
- Modify: `frontend/src/components/storyteller/day/DayControlPanel.vue`
- Create: `frontend/tests/storyteller-vote-board.test.js`
- Create: `frontend/tests/storyteller-day-resolution.test.js`

**Interfaces:**
- Consumes: Task 1 presentation helpers and `view.current`, `view.nominations`, `view.quorum`, `view.seats`, `view.travelers`.
- Produces: events `toggle-vote(participant)`, `resolve-nomination(passed)`, and `end-day`; all consequential actions use two-step confirmation.

- [ ] **Step 1: Write failing live-vote, resolution, and concurrent-update tests**

```js
it('updates from a player vote projection without clearing the nomination draft', async () => {
  const wrapper = mount(DayControlPanel, { props: { view: makeStorytellerDayView({ current: activeNomination([]) }), connected: true } })
  await wrapper.setProps({ view: makeStorytellerDayView({ current: activeNomination([2]) }) })
  expect(wrapper.get('[data-voter="2"]').classes()).toContain('on')
})

it('shows an unresolved-nomination error and rearms end-day confirmation', async () => {
  const wrapper = mount(DayResolution, { props: { view: makeStorytellerDayView({ current: activeNomination([]) }), error: new Error('先结算当前提名') } })
  expect(wrapper.text()).toContain('先结算当前提名')
  expect(wrapper.get('[data-end-day]').text()).toContain('结束白天')
})
```

Cover quorum coloring, living votes, unused and spent dead votes, traveler votes, pass/fail buttons, unique execution leader, tie/no-execution message, grouped history, and end-day two-click confirmation.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `cd frontend && npm test -- tests/storyteller-vote-board.test.js tests/storyteller-day-resolution.test.js`

Expected: FAIL because the components do not exist.

- [ ] **Step 3: Implement projection-driven voting and resolution components**

`VoteBoard` derives button state on every render from `view.current.votes` and never owns a shadow vote list. `DayResolution` emits pass/fail or end-day only after confirmation and cancels its armed state on a failed command signal. `NominationHistory` uses the pure grouped nomination and death histories, marks passed, failed, executed, exile and tie states, and shows the pending execution leader without editing server data.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `cd frontend && npm test -- tests/storyteller-vote-board.test.js tests/storyteller-day-resolution.test.js tests/storyteller-day-composer.test.js`

Expected: PASS for concurrent updates, vote eligibility, resolution and end-day errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/storyteller/day frontend/tests/storyteller-vote-board.test.js frontend/tests/storyteller-day-resolution.test.js
git commit -m "feat: add storyteller daytime voting"
```

### Task 4: Integrate the day workflow and complete regression acceptance

**Files:**
- Modify: `frontend/src/components/storyteller/StorytellerLiveView.vue`
- Modify: `frontend/src/components/storyteller/GameControlPanel.vue`
- Modify: `frontend/src/components/storyteller/ContextPanel.vue`
- Modify: `frontend/src/styles/storyteller.css`
- Modify: `docs/migration/vue-vite-status.md`
- Create: `frontend/tests/storyteller-day-flow.test.js`

**Interfaces:**
- Consumes: Tasks 1-3 day service/components and existing `useStorytellerCommand`.
- Produces: Vue storyteller daytime workflow with command keys `day:stage`, `day:nomination`, `day:vote:<id>`, `day:resolve`, and `day:end`.

- [ ] **Step 1: Write failing full-flow integration tests**

```js
it('runs stage, nomination, vote, resolution and end-day commands in Vue', async () => {
  const wrapper = mount(StorytellerLiveView, { props: { password: 'secret' }, global: dayFlowStubs() })
  await emitDayCommand(wrapper, 'set-stage', 'nom')
  await emitDayCommand(wrapper, 'start-nomination', { nominator: 1, nominee: 2 })
  await emitDayCommand(wrapper, 'toggle-vote', 1)
  await emitDayCommand(wrapper, 'resolve-nomination', true)
  await emitDayCommand(wrapper, 'end-day')
  expect(dayServiceCalls()).toEqual(['stage:nom', 'nomination:1:2', 'vote:1', 'resolve:true', 'end'])
})

it('does not render the legacy day link during day phase', () => {
  const wrapper = mount(GameControlPanel, { props: { view: makeStorytellerDayView(), connected: true } })
  expect(wrapper.find('a[href="/legacy/#/storyteller"]').exists()).toBe(false)
})
```

- [ ] **Step 2: Run integration tests and verify RED**

Run: `cd frontend && npm test -- tests/storyteller-day-flow.test.js`

Expected: FAIL because `GameControlPanel` still shows the legacy fallback and day commands are not wired.

- [ ] **Step 3: Integrate commands and stable desktop layout**

`StorytellerLiveView` exposes day handlers through `run`; `GameControlPanel` renders `DayControlPanel` for `phase === 'day'`; `ContextPanel` continues showing selected-seat information without replacing the left day controls. Add a fixed internal scroll area and sticky resolution footer so controls do not move when history grows.

- [ ] **Step 4: Run the complete frontend and backend suites**

Run: `cd frontend && npm test && npm run build && cd ../backend && /Users/lichenxi/botc-grimoire/backend/.venv/bin/python -m unittest discover -s tests -v && /Users/lichenxi/botc-grimoire/backend/.venv/bin/python -m compileall app tests`

Expected: all frontend and backend tests pass, the Vite production build succeeds, and Python compilation has no errors.

- [ ] **Step 5: Run isolated smoke verification**

Run in terminal A: `cd backend && /Users/lichenxi/botc-grimoire/backend/.venv/bin/python tools/run_test_server.py`

Run in terminal B: `cd backend && SMOKE_BASE=http://127.0.0.1:8001 /Users/lichenxi/botc-grimoire/backend/.venv/bin/python smoke_test.py`

Expected: the smoke test reports all existing join, setup, night, nomination, vote, save and WebSocket checks passing without touching `backend/data/game.json`; then stop terminal A with Ctrl+C.

- [ ] **Step 6: Perform browser acceptance**

Open the isolated server and verify:

```text
360x800 player: lobby, night prompt, day nomination, chat and result have no horizontal overflow.
1366x768 storyteller: stage, composer, live votes, history and end-day stay usable with the action footer fixed.
Concurrent check: cast a player vote in the phone-width tab and observe the desktop vote board update.
Console: no errors or warnings from either page.
```

Expected: every state is operable and visible at the stated viewport, with real-time synchronization.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/storyteller/StorytellerLiveView.vue frontend/src/components/storyteller/GameControlPanel.vue frontend/src/components/storyteller/ContextPanel.vue frontend/src/styles/storyteller.css frontend/tests/storyteller-day-flow.test.js docs/migration/vue-vite-status.md
git commit -m "feat: complete Vue storyteller day workflow"
```
