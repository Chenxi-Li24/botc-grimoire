# Vue Player Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep joined and returning players in a complete mobile-first Vue player application for lobby, night, day, chat, and result states.

**Architecture:** Preserve FastAPI and WebSocket contracts as the server-authoritative boundary. Add a player WebSocket composable, a focused player command service, pure presentation helpers, and small components under `frontend/src/components/player/`; add one player-authenticated canonical night-action bridge so phone choices feed the migrated night engine.

**Tech Stack:** Vue 3, Vite 8, Vitest 5, `@vue/test-utils`, FastAPI, Python `unittest`.

**Spec:** `docs/superpowers/specs/2026-09-20-player-day-vue-migration-design.md`

## Global Constraints

- Existing REST endpoints, WebSocket projections, local-storage identity, and the JSON save format remain compatible.
- The server is authoritative; the client stores only temporary selections, drafts, expanded state, and result-tab state.
- A player projection must never expose another player's private role, alignment, effects, or adjudication facts.
- No new frontend runtime dependency is added.
- `frontend/legacy/` remains available only for explicit non-goals; normal player play must never load it.
- The player UI is mobile-first and must work at a 360-pixel viewport without horizontal document overflow.

## Review Focus

- A stored player ID becomes invalid while connected: Task 1 tests that the ID is cleared and the join page replaces the player page.
- A night step changes while a player has unsent targets: Task 4 tests that stale selections are discarded and cannot be submitted against the new step.
- A traveler string ID appears beside numeric seat IDs: Task 5 tests labels, nomination targets, and voting without numeric coercion.
- A WebSocket redraw arrives while a chat message is being typed: Task 6 tests that the unsent draft remains intact.
- A player receives a projection containing only public seat data: Task 3 tests that no component attempts to infer other players' private roles.

---

### Task 1: Route valid player sessions into Vue

**Files:**
- Create: `frontend/src/pages/PlayerPage.vue`
- Create: `frontend/src/composables/usePlayerView.js`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/services/navigation.js`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_player_websocket_session.py`
- Test: `frontend/tests/player-routing.test.js`
- Test: `frontend/tests/player-view.test.js`

**Interfaces:**
- Consumes: `getPlayerId(): string | null`, `clearPlayerId(): void`, and `openSocket({ query, onMessage, onStatus, onFatal })`.
- Produces: `resolveEntry(...): 'join' | { vuePage: 'storyteller' | 'player' } | redirect`, `usePlayerView(playerId, { onInvalid }): { view, connectionStatus }`, and `<PlayerPage player-id="..." @invalid>`.

- [ ] **Step 1: Write failing routing and socket lifecycle tests**

```js
it('keeps a valid returning player in Vue', async () => {
  await expect(resolveEntry({ hash: '', playerId: 'p1', validatePlayer: vi.fn().mockResolvedValue({}) }))
    .resolves.toEqual({ vuePage: 'player' })
})

it('clears an invalid live session through the page event', async () => {
  const wrapper = mount(App)
  await flushPromises()
  expect(wrapper.find('[data-player-page]').exists()).toBe(true)
  await wrapper.findComponent(PlayerPage).vm.$emit('invalid')
  expect(clearPlayerId).toHaveBeenCalled()
})
```

`player-view.test.js` uses the existing fake WebSocket pattern and asserts `query === 'who=p1'`, status transitions, projection replacement, cleanup on unmount, and fatal close code `4001` calling `onInvalid`.

The backend test connects a player socket, removes that player, calls `hub.push_all()`, and asserts the socket is closed with code `4001` and removed from `hub.players`.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `cd frontend && npm test -- tests/player-routing.test.js tests/player-view.test.js && cd ../backend && /Users/lichenxi/botc-grimoire/backend/.venv/bin/python -m unittest tests.test_player_websocket_session -v`

Expected: FAIL because valid players still resolve to `{ legacyUrl: '/legacy/' }`, the player page/composable do not exist, and removed-player sockets stay open.

- [ ] **Step 3: Implement Vue routing and the player view composable**

```js
// services/navigation.js
if (playerId) {
  try {
    await validatePlayer(playerId)
    return { vuePage: 'player' }
  } catch {
    return 'join'
  }
}
```

```js
// composables/usePlayerView.js
export function usePlayerView(playerId, { onInvalid = () => {} } = {}) {
  const view = shallowRef(null)
  const connectionStatus = ref('connecting')
  const connection = openSocket({
    query: `who=${encodeURIComponent(playerId)}`,
    onMessage: (next) => { view.value = next },
    onStatus: (next) => { connectionStatus.value = next },
    onFatal: onInvalid,
  })
  onBeforeUnmount(() => connection.close())
  return { view, connectionStatus }
}
```

`App.vue` stores the active player ID, changes `onJoined(playerId)` to render `player`, renders `PlayerPage`, and handles `invalid` by clearing storage and returning to `join`. `PlayerPage.vue` initially renders connection state and emits `invalid` from the composable callback.

`Hub.push_all()` closes every socket for a player ID no longer in `game.players` with code `4001`, removes that entry from `hub.players`, and continues broadcasting to valid players.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run: `cd frontend && npm test -- tests/player-routing.test.js tests/player-view.test.js tests/app-routing.test.js tests/join-page.test.js && cd ../backend && /Users/lichenxi/botc-grimoire/backend/.venv/bin/python -m unittest tests.test_player_websocket_session -v`

Expected: PASS with valid and newly joined sessions staying in Vue and invalid sessions returning to join.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.vue frontend/src/pages/PlayerPage.vue frontend/src/composables/usePlayerView.js frontend/src/services/navigation.js frontend/tests/player-routing.test.js frontend/tests/player-view.test.js frontend/tests/app-routing.test.js backend/app/main.py backend/tests/test_player_websocket_session.py
git commit -m "feat: route player sessions into Vue"
```

### Task 2: Add player commands and safe presentation helpers

**Files:**
- Create: `frontend/src/services/player.js`
- Create: `frontend/src/composables/usePlayerActions.js`
- Create: `frontend/src/presentation/player.js`
- Test: `frontend/tests/player-service.test.js`
- Test: `frontend/tests/player-presentation.test.js`
- Test: `frontend/tests/player-actions.test.js`

**Interfaces:**
- Consumes: `api(path, init)`.
- Produces: `createPlayerService(playerId)` methods `sit`, `setWish`, `joinTraveler`, `nominate`, `vote`, `submitNightAction`, `createChat`, `respondInvite`, `requestChat`, `inviteMore`, `approveRequest`, `sendChat`, `leaveChat`, and `closeChat`; `usePlayerActions({ service, connected })`; pure `participantLabel`, `teamLabel`, `phaseLabel`, `groupDeaths`, and `groupNominations` helpers.

- [ ] **Step 1: Write failing service, action-state, and presentation tests**

```js
it('preserves traveler ids in commands and labels', async () => {
  const service = createPlayerService('p/1')
  await service.nominate('t2')
  expect(fetch).toHaveBeenCalledWith('/api/player/p%2F1/nominate', expect.objectContaining({
    method: 'POST', body: JSON.stringify({ nominee: 't2' }),
  }))
  expect(participantLabel('t2', [], [{ id: 't2', name: '阿旅' }])).toBe('🎒 阿旅')
})

it('keeps only one pending invocation for the same key', async () => {
  const deferred = Promise.withResolvers()
  const actions = usePlayerActions({ connected: ref(true) })
  const first = actions.run('vote', () => deferred.promise)
  const second = actions.run('vote', vi.fn())
  expect(await second).toBeNull()
  deferred.resolve({ ok: true })
  await first
})
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `cd frontend && npm test -- tests/player-service.test.js tests/player-presentation.test.js tests/player-actions.test.js`

Expected: FAIL because the player modules do not exist.

- [ ] **Step 3: Implement exact command mappings and pure helpers**

```js
const playerPath = (id, suffix) => `/api/player/${encodeURIComponent(id)}${suffix}`
const post = (path, body) => api(path, {
  method: 'POST',
  ...(body === undefined ? {} : { body: JSON.stringify(body) }),
})

export function createPlayerService(playerId) {
  const withId = (suffix) => playerPath(playerId, suffix)
  const chat = (cid, suffix) => `/api/chat/${cid}${suffix}?player_id=${encodeURIComponent(playerId)}`
  return {
    sit: (seat) => post(withId('/sit'), { seat }),
    setWish: (wish) => post(withId('/wish'), { wish }),
    joinTraveler: () => post(withId('/traveler')),
    nominate: (nominee) => post(withId('/nominate'), { nominee }),
    vote: () => post(withId('/vote')),
    submitNightAction: (payload) => post(withId('/night-action'), payload),
    createChat: (invitees) => post(`/api/chat/create?player_id=${encodeURIComponent(playerId)}`, { invitees }),
    respondInvite: (cid, accept) => post(chat(cid, '/invite'), { accept }),
    requestChat: (cid) => post(chat(cid, '/request')),
    inviteMore: (cid, invitees) => post(chat(cid, '/invite-more'), { invitees }),
    approveRequest: (cid, who, approve) => post(chat(cid, '/approve'), { who, approve }),
    sendChat: (cid, text) => post(chat(cid, '/send'), { text }),
    leaveChat: (cid) => post(chat(cid, '/leave')),
    closeChat: (cid) => post(chat(cid, '/close')),
  }
}
```

`usePlayerActions` mirrors the established storyteller pending/error wrapper while refusing calls when disconnected or already pending. Presentation helpers treat numeric seats and traveler strings as distinct values, group deaths/nominations without mutation, and accept only fields in the player projection.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `cd frontend && npm test -- tests/player-service.test.js tests/player-presentation.test.js tests/player-actions.test.js`

Expected: PASS for every command mapping, duplicate prevention, error retention, and mixed participant IDs.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/services/player.js frontend/src/composables/usePlayerActions.js frontend/src/presentation/player.js frontend/tests/player-service.test.js frontend/tests/player-presentation.test.js frontend/tests/player-actions.test.js
git commit -m "feat: add Vue player command layer"
```

### Task 3: Migrate lobby, role card, and public board

**Files:**
- Create: `frontend/src/components/player/PlayerShell.vue`
- Create: `frontend/src/components/player/PlayerLobby.vue`
- Create: `frontend/src/components/player/PlayerRoleCard.vue`
- Create: `frontend/src/components/player/PlayerBoard.vue`
- Create: `frontend/tests/fixtures/playerView.js`
- Modify: `frontend/src/pages/PlayerPage.vue`
- Test: `frontend/tests/player-lobby.test.js`
- Test: `frontend/tests/player-role-card.test.js`
- Test: `frontend/tests/player-board.test.js`

**Interfaces:**
- Consumes: Task 1 `usePlayerView`; Task 2 `createPlayerService`, `usePlayerActions`, and label helpers.
- Produces: `PlayerShell` slots `header/default/actions`; `PlayerLobby` events `sit`, `wish`, `traveler`; `PlayerBoard` event `select-participant`; `PlayerRoleCard` renders only `view.me`, `view.traveler`, `view.role_changed`, `view.team_changed`, `view.bluffs`, `view.demon_seats`, `view.minion_seats`, and `view.lunatic_seats`.

- [ ] **Step 1: Write failing component tests using player-shaped fixtures**

```js
it('never displays another seat private role', () => {
  const view = makePlayerView({
    me: { id: 'p1', name: '阿青', seat: 1, role: { id: 'chef', name: '厨师', team: 'townsfolk' } },
    seats: [{ seat: 1, player: { name: '阿青' } }, { seat: 2, player: { name: '小白' } }],
  })
  const wrapper = mount(PlayerBoard, { props: { view } })
  expect(wrapper.text()).toContain('小白')
  expect(wrapper.text()).not.toContain('小恶魔')
})

it('keeps identity hidden before start and emits a seat choice', async () => {
  const wrapper = mount(PlayerLobby, { props: { view: makeLobbyPlayerView() } })
  expect(wrapper.text()).not.toContain('厨师')
  await wrapper.get('[data-seat="2"]').trigger('click')
  expect(wrapper.emitted('sit')).toEqual([[2]])
})
```

Role-card tests cover hidden/revealed state, perceived identity, changed role/alignment, madness, bluffs, Demon/Minion/Lunatic meetings, official composition, Sentinel and fabled notices.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `cd frontend && npm test -- tests/player-lobby.test.js tests/player-role-card.test.js tests/player-board.test.js`

Expected: FAIL because the components and fixture do not exist.

- [ ] **Step 3: Implement the components and connect them in PlayerPage**

```vue
<!-- PlayerPage.vue composition boundary -->
<PlayerShell v-if="view" :view="view" :connection-status="connectionStatus">
  <PlayerLobby
    v-if="view.status === 'lobby'"
    :view="view"
    :connected="connected"
    :pending="pending"
    @sit="run('sit', () => service.sit($event))"
    @wish="run('wish', () => service.setWish($event))"
    @traveler="run('traveler', () => service.joinTraveler())"
  />
  <template v-else>
    <PlayerRoleCard :view="view" />
    <PlayerBoard :view="view" @select-participant="selectedParticipant = $event" />
  </template>
</PlayerShell>
```

Use buttons rather than clickable `div` elements, keep card-hiding state inside `PlayerRoleCard`, and never pass the storyteller view to player components.

- [ ] **Step 4: Run focused and routing tests and verify GREEN**

Run: `cd frontend && npm test -- tests/player-lobby.test.js tests/player-role-card.test.js tests/player-board.test.js tests/player-routing.test.js`

Expected: PASS with lobby commands emitted, player privacy preserved, and Vue routing intact.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/player frontend/src/pages/PlayerPage.vue frontend/tests/fixtures/playerView.js frontend/tests/player-lobby.test.js frontend/tests/player-role-card.test.js frontend/tests/player-board.test.js
git commit -m "feat: migrate player lobby and role card"
```

### Task 4: Bridge player night actions into the canonical night engine

**Files:**
- Create: `backend/app/night/player_actions.py`
- Modify: `backend/app/api/schemas.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/game.py`
- Create: `backend/tests/test_player_night_actions.py`
- Create: `frontend/src/components/player/PlayerNightAction.vue`
- Modify: `frontend/src/pages/PlayerPage.vue`
- Modify: `frontend/src/composables/useNightWorkflow.js`
- Modify: `frontend/tests/fixtures/playerView.js`
- Test: `frontend/tests/player-night-action.test.js`
- Modify: `frontend/tests/night-workflow.test.js`

**Interfaces:**
- Consumes: current `NightService` methods and player session ownership from `GameManager.players`.
- Produces: `POST /api/player/{player_id}/night-action` body `{ step_id, selected_seats, character_id? }`; `submit_player_night_action(game, player_id, body) -> Any`; safe player prompt selection fields `target_seats`, `player_count`, `character_candidates`, `allow_self`, and `alive_only`; `PlayerNightAction` event `submit`; storyteller draft hydration from canonical `step.values`.

- [ ] **Step 1: Write failing backend authorization/dispatch tests**

```python
def test_player_action_rejects_another_seats_step(self):
    step = next(item for item in self.game.night.queue.steps if item.actor_seat == 2)
    self.game.night.queue.current_step_id = step.id
    with self.assertRaisesRegex(ValueError, "不是你的夜晚步骤"):
        submit_player_night_action(self.game, "player-at-seat-1", {
            "step_id": step.id, "selected_seats": [3],
        })

def test_demon_player_choice_creates_pending_outcome(self):
    step = next(item for item in self.game.night.queue.steps
                if item.actor_seat == 1 and item.character_id == "imp")
    self.game.night.queue.current_step_id = step.id
    result = submit_player_night_action(self.game, "demon-player", {
        "step_id": step.id, "selected_seats": [2],
    })
    self.assertEqual(result.selected_seats, [2])
    pending = list(self.game.pending_outcomes.values())[-1]
    self.assertEqual(pending.metadata["step_id"], step.id)
```

Cover stale/non-current steps, target validation, Lunatic choice-only pending outcome, information preparation, Poisoner/Widow/Cerenovus effect dispatch, Pit-Hag preview creation, and save/reload persistence.

- [ ] **Step 2: Run backend tests and verify RED**

Run: `cd backend && /Users/lichenxi/botc-grimoire/backend/.venv/bin/python -m unittest tests.test_player_night_actions -v`

Expected: FAIL because the player canonical-night dispatcher and request schema do not exist.

- [ ] **Step 3: Implement the authenticated canonical dispatcher and endpoint**

```python
class PlayerNightActionBody(BaseModel):
    step_id: str
    selected_seats: list[int] = Field(default_factory=list)
    character_id: str | None = None
```

```python
def submit_player_night_action(game, player_id: str, body: dict):
    player = game.players.get(player_id)
    if player is None or player.seat is None:
        raise ValueError("你还没有入座")
    step = game.night.step(body["step_id"])
    if step.id != game.night.queue.current_step_id or step.actor_seat != player.seat:
        raise ValueError("这不是你的夜晚步骤")
    return dispatch_current_player_action(
        game.night, step, body.get("selected_seats", []), body.get("character_id")
    )
```

The dispatcher uses the same branches as `NightTaskPanel`: status-role effects apply immediately, information roles prepare a draft/delivery, Demon/Lunatic choices create a pending outcome, Pit-Hag creates a private preview, and remaining roles record a selection. The endpoint saves and broadcasts only after success. `_player_night_workflow` expands only the current player's prompt with legal target seat numbers, required target count and safe character candidates; it never includes real roles, effects or adjudication data for other seats.

- [ ] **Step 4: Write failing Vue night-action tests**

```js
it('drops a draft when the current step changes', async () => {
  const wrapper = mount(PlayerNightAction, { props: { view: makeNightPlayerView('step-1') } })
  await wrapper.get('[data-target="2"]').trigger('click')
  await wrapper.setProps({ view: makeNightPlayerView('step-2') })
  expect(wrapper.find('[data-target="2"]').classes()).not.toContain('on')
})

it('submits only the projected current player step', async () => {
  const wrapper = mount(PlayerNightAction, { props: { view: makeNightPlayerView('step-1'), connected: true } })
  await wrapper.get('[data-target="2"]').trigger('click')
  await wrapper.get('[data-submit-night]').trigger('click')
  expect(wrapper.emitted('submit')[0][0]).toEqual({ step_id: 'step-1', selected_seats: [2] })
})
```

- [ ] **Step 5: Run Vue tests and verify RED**

Run: `cd frontend && npm test -- tests/player-night-action.test.js tests/night-workflow.test.js`

Expected: FAIL because `PlayerNightAction` and canonical-value hydration do not exist.

- [ ] **Step 6: Implement player night UI and storyteller hydration**

`PlayerNightAction` renders only `view.night_workflow.prompt`, its safe `target_seats` and `character_candidates`, public participant names from `view.seats`, `night_workflow.deliveries`, the temporary Widow grimoire projection when present, madness and Lunatic context. It watches `prompt.id` and clears target/character drafts on change. `useNightWorkflow` seeds its drafts from `currentTask.values.targets` and `currentTask.values.character`, so a phone submission appears immediately in the storyteller task panel.

- [ ] **Step 7: Run backend and frontend tests and verify GREEN**

Run: `cd backend && /Users/lichenxi/botc-grimoire/backend/.venv/bin/python -m unittest tests.test_player_night_actions tests.test_night_api -v && cd ../frontend && npm test -- tests/player-night-action.test.js tests/night-workflow.test.js tests/night-task-panel.test.js`

Expected: PASS with player choices visible in the canonical storyteller workflow and stale/foreign actions rejected.

- [ ] **Step 8: Commit**

```bash
git add backend/app/night/player_actions.py backend/app/api/schemas.py backend/app/main.py backend/app/game.py backend/tests/test_player_night_actions.py frontend/src/components/player/PlayerNightAction.vue frontend/src/pages/PlayerPage.vue frontend/src/composables/useNightWorkflow.js frontend/tests/fixtures/playerView.js frontend/tests/player-night-action.test.js frontend/tests/night-workflow.test.js
git commit -m "feat: connect player night actions to workflow"
```

### Task 5: Migrate player daytime nominations and voting

**Files:**
- Create: `frontend/src/components/player/PlayerDayAction.vue`
- Create: `frontend/src/components/player/PublicTimeline.vue`
- Modify: `frontend/src/pages/PlayerPage.vue`
- Test: `frontend/tests/player-day-action.test.js`
- Test: `frontend/tests/public-timeline.test.js`

**Interfaces:**
- Consumes: Task 2 service methods and participant/death/nomination helpers; Task 3 `PlayerBoard` participant selection.
- Produces: `PlayerDayAction` events `nominate` and `vote`; `PublicTimeline` read-only deaths and nominations; selection values retain `number | string`.

- [ ] **Step 1: Write failing day-action and timeline tests**

```js
it('nominates a traveler without coercing its id', async () => {
  const wrapper = mount(PlayerDayAction, { props: { view: makeDayPlayerView(), connected: true } })
  await wrapper.get('[data-nominee="t1"]').trigger('click')
  await wrapper.get('[data-confirm-nomination]').trigger('click')
  expect(wrapper.emitted('nominate')).toEqual([['t1']])
})

it('requires confirmation before spending the only dead vote', async () => {
  const wrapper = mount(PlayerDayAction, { props: { view: makeDeadPlayerVoteView(), connected: true } })
  await wrapper.get('[data-vote]').trigger('click')
  expect(wrapper.emitted('vote')).toBeUndefined()
  await wrapper.get('[data-vote]').trigger('click')
  expect(wrapper.emitted('vote')).toHaveLength(1)
})
```

Timeline tests cover public deaths grouped by day, current live vote chips, passed/failed/executed history, empty seats and traveler labels.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `cd frontend && npm test -- tests/player-day-action.test.js tests/public-timeline.test.js`

Expected: FAIL because the day components do not exist.

- [ ] **Step 3: Implement day controls and timeline**

`PlayerDayAction` derives permission from `status`, `phase`, `day_stage`, `current`, the player's alive/dead-vote state, and same-day nomination history. It exposes a local nominee confirmation strip, supports seats and travelers, and uses a two-click `ConfirmAction` for a dead vote. `PublicTimeline` stays read-only and renders only public projection fields.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `cd frontend && npm test -- tests/player-day-action.test.js tests/public-timeline.test.js tests/player-presentation.test.js`

Expected: PASS for numeric and traveler targets, vote toggling, dead-vote confirmation, and public history.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/player/PlayerDayAction.vue frontend/src/components/player/PublicTimeline.vue frontend/src/pages/PlayerPage.vue frontend/tests/player-day-action.test.js frontend/tests/public-timeline.test.js
git commit -m "feat: migrate player nominations and voting"
```

### Task 6: Migrate player private chat

**Files:**
- Create: `frontend/src/components/player/PlayerChat.vue`
- Modify: `frontend/src/pages/PlayerPage.vue`
- Test: `frontend/tests/player-chat.test.js`

**Interfaces:**
- Consumes: Task 2 chat service methods and `view.chat`.
- Produces: chat events `{ type, cid?, invitees?, who?, approve?, text? }`; preserves `messageDraft` while `view.chat` changes.

- [ ] **Step 1: Write failing chat workflow and draft-retention tests**

```js
it('keeps the unsent message across a WebSocket projection update', async () => {
  const wrapper = mount(PlayerChat, { props: { chat: activeChatView() } })
  await wrapper.get('[data-chat-draft]').setValue('还没发出的内容')
  await wrapper.setProps({ chat: { ...activeChatView(), chats_public: [{ id: 2, color: '#fff' }] } })
  expect(wrapper.get('[data-chat-draft]').element.value).toBe('还没发出的内容')
})

it('emits an exact send command and clears only after success notification', async () => {
  const wrapper = mount(PlayerChat, { props: { chat: activeChatView() } })
  await wrapper.get('[data-chat-draft]').setValue('你好')
  await wrapper.get('[data-chat-send]').trigger('click')
  expect(wrapper.emitted('command')[0][0]).toEqual({ type: 'send', cid: 1, text: '你好' })
})
```

Cover create/invite selection, invitation response, join request, owner approval, invite-more, leave, close, storyteller participant label, and errors that retain input.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `cd frontend && npm test -- tests/player-chat.test.js`

Expected: FAIL because `PlayerChat` does not exist.

- [ ] **Step 3: Implement chat states and command mapping in PlayerPage**

`PlayerChat` receives chat state and emits semantic commands without calling APIs. `PlayerPage` maps each command to the exact Task 2 service method through `run('chat:<type>:<cid>', ...)`; it calls a child-exposed `markSent()` only after a successful send so failures preserve the draft.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run: `cd frontend && npm test -- tests/player-chat.test.js tests/player-service.test.js tests/player-actions.test.js`

Expected: PASS for all chat states, preserved drafts, and exact API mapping.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/player/PlayerChat.vue frontend/src/pages/PlayerPage.vue frontend/tests/player-chat.test.js
git commit -m "feat: migrate player private chat"
```

### Task 7: Add result/review views and complete the player cutover

**Files:**
- Create: `frontend/src/components/player/PlayerResult.vue`
- Create: `frontend/src/styles/player.css`
- Modify: `frontend/src/pages/PlayerPage.vue`
- Modify: `frontend/src/main.js`
- Modify: `docs/migration/vue-vite-status.md`
- Test: `frontend/tests/player-result.test.js`
- Test: `frontend/tests/player-page.test.js`

**Interfaces:**
- Consumes: all prior player components and player projection result/review fields.
- Produces: a complete `[data-player-page]` at all game states with no normal `/legacy/` navigation.

- [ ] **Step 1: Write failing result and full-page state tests**

```js
it('shows win state and switches to the grouped review', async () => {
  const wrapper = mount(PlayerResult, { props: { view: makeFinishedPlayerView({ winner: 'good' }) } })
  expect(wrapper.text()).toContain('你赢了')
  await wrapper.get('[data-result-tab="review"]').trigger('click')
  expect(wrapper.text()).toContain('第 1 夜')
  expect(wrapper.text()).toContain('信息错误')
})

it.each(['lobby', 'night', 'day', 'finished'])('renders %s without a legacy link', (state) => {
  const wrapper = mount(PlayerPage, { props: { playerId: 'p1' }, global: playerPageStubs(state) })
  expect(wrapper.find('a[href^="/legacy"]').exists()).toBe(false)
})
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `cd frontend && npm test -- tests/player-result.test.js tests/player-page.test.js`

Expected: FAIL because result/review and full-page state composition are incomplete.

- [ ] **Step 3: Implement result/review, responsive styles, and status documentation**

`PlayerResult` computes the player's real winning team from traveler alignment or the player's final role/alignment, renders all revealed seats/travelers, and switches locally between settlement and read-only review groups. `player.css` uses a single-column mobile layout, 44-pixel minimum controls, sticky action area, wrapped chips, and no fixed content width. Import it from `main.js` and mark the player page migrated in the status document.

- [ ] **Step 4: Run player and complete frontend verification**

Run: `cd frontend && npm test && npm run build`

Expected: all Vitest files pass and Vite production build succeeds.

- [ ] **Step 5: Run backend regression required by the new endpoint**

Run: `cd backend && /Users/lichenxi/botc-grimoire/backend/.venv/bin/python -m unittest discover -s tests -v && /Users/lichenxi/botc-grimoire/backend/.venv/bin/python -m compileall app tests`

Expected: all backend tests pass and compilation completes without errors.

- [ ] **Step 6: Perform phone-width browser acceptance**

Before committing, open the isolated application at a 360x800 viewport and verify lobby, night, day, chat and result states have no document-level horizontal overflow, all primary controls are at least 44 pixels tall, and browser console output contains no warnings or errors.

Expected: all five player states are usable at phone width and remain on the Vue root route.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/player/PlayerResult.vue frontend/src/styles/player.css frontend/src/pages/PlayerPage.vue frontend/src/main.js frontend/tests/player-result.test.js frontend/tests/player-page.test.js docs/migration/vue-vite-status.md
git commit -m "feat: complete Vue player experience"
```
