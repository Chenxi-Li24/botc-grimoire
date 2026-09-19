# Storyteller Vue Shell and Grimoire Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a safe Vue preview of the storyteller's desktop three-column shell, live read-only grimoire, join context, and selected-player details without replacing the complete legacy storyteller console.

**Architecture:** Add a private migration route at `/#/storyteller-preview` while preserving `/#/storyteller -> /legacy/#/storyteller`. The preview owns one authenticated reconnecting WebSocket projection, passes immutable view data into focused presentation components, and offers an explicit link back to the complete legacy controls. This is migration slices 1-2 of the storyteller layout spec; state-changing setup and game-flow controls remain in later plans.

**Tech Stack:** Vue 3 Composition API, Vite 8, Vitest 5, Vue Test Utils, native WebSocket, existing FastAPI REST/WebSocket contracts.

**Spec:** `docs/superpowers/specs/2026-09-20-storyteller-desktop-layout-design.md`

## Global Constraints

- Optimize for computer use with `1366x768` as the minimum primary viewport.
- Use a `260px minmax(560px, 1fr) 320px` desktop grid, 16 px gaps, 64 px header, and `100dvh` shell.
- The document body must not scroll; only the left and right panels may scroll independently.
- At widths below 1180 px, side panels become overlay drawers; no separate storyteller phone workflow is introduced.
- Preserve all REST/WebSocket payloads, local-storage keys, and JSON save compatibility.
- Keep `/#/storyteller` routed to `/legacy/#/storyteller` until every storyteller workflow has migrated.
- The preview is read-only except for authentication; every state-changing workflow links back to the complete legacy console.
- Do not add dependencies, backend behavior, database support, multi-room support, or new game rules.

## Review Focus

- A bad storyteller password must return the preview to its login form, stop reconnecting, clear only `botc_st_password`, and preserve `botc_player_id`; pinned in Task 3.
- A transient WebSocket close must keep the latest grimoire visible and schedule one reconnect instead of clearing the view; pinned in Tasks 2 and 3.
- A server update that removes the selected player must clear the right-panel selection instead of showing stale private data; pinned in Task 6.
- The migration preview must never intercept the production `/#/storyteller` route; pinned in Task 1.
- At exactly 1366x768 the page must have no document-level overflow while the board and right-panel heading remain visible; pinned by the browser acceptance script in Task 7.

---

## Planned File Structure

```text
frontend/src/
  App.vue
  services/
    navigation.js
    session.js
    websocket.js
  composables/
    useStorytellerView.js
  pages/
    StorytellerPreviewPage.vue
  components/storyteller/
    StorytellerLogin.vue
    StorytellerLiveView.vue
    StorytellerShell.vue
    StorytellerHeader.vue
    GameControlPanel.vue
    GrimoireBoard.vue
    SeatNode.vue
    ContextPanel.vue
    JoinPanel.vue
    PlayerDetailPanel.vue
  presentation/
    storyteller.js
  styles/
    storyteller.css
frontend/tests/
  fixtures/storytellerView.js
  app-preview-routing.test.js
  websocket.test.js
  storyteller-login.test.js
  storyteller-view.test.js
  storyteller-shell.test.js
  grimoire-board.test.js
  storyteller-context.test.js
```

---

### Task 1: Add a Preview-Only Vue Route

**Files:**
- Modify: `frontend/src/services/navigation.js`
- Modify: `frontend/src/App.vue`
- Create: `frontend/src/pages/StorytellerPreviewPage.vue`
- Create: `frontend/tests/app-preview-routing.test.js`
- Modify: `frontend/tests/app-routing.test.js`

**Interfaces:**
- Consumes: existing `resolveEntry({ hash, playerId, validatePlayer })` and `App.vue` route-version protection.
- Produces: destination `{ vuePage: 'storyteller-preview' }` for `#/storyteller-preview`; `StorytellerPreviewPage` mounted only for that destination.

- [ ] **Step 1: Write the failing routing tests**

Add to `frontend/tests/app-routing.test.js`:

```js
it('keeps the complete storyteller route on legacy', async () => {
  await expect(resolveEntry({
    hash: '#/storyteller', playerId: null, validatePlayer: vi.fn(),
  })).resolves.toEqual({ legacyUrl: '/legacy/#/storyteller' })
})

it('opens only the explicit storyteller preview in Vue', async () => {
  await expect(resolveEntry({
    hash: '#/storyteller-preview', playerId: null, validatePlayer: vi.fn(),
  })).resolves.toEqual({ vuePage: 'storyteller-preview' })
})
```

Create `frontend/tests/app-preview-routing.test.js`:

```js
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, expect, it, vi } from 'vitest'
import App from '../src/App.vue'
import { resolveEntry } from '../src/services/navigation.js'

vi.mock('../src/services/api.js', () => ({ api: vi.fn() }))
vi.mock('../src/services/navigation.js', () => ({
  goToLegacy: vi.fn(),
  resolveEntry: vi.fn(),
}))
vi.mock('../src/services/session.js', () => ({
  clearPlayerId: vi.fn(),
  getPlayerId: vi.fn().mockReturnValue(null),
}))

beforeEach(() => vi.clearAllMocks())

it('renders the Vue storyteller preview destination', async () => {
  resolveEntry.mockResolvedValue({ vuePage: 'storyteller-preview' })
  const wrapper = mount(App)
  await flushPromises()
  expect(wrapper.get('[data-storyteller-preview]').exists()).toBe(true)
})
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `npm --prefix frontend test -- --run tests/app-routing.test.js tests/app-preview-routing.test.js`

Expected: FAIL because the preview route and preview component do not exist.

- [ ] **Step 3: Implement the preview destination**

In `resolveEntry`, check the longer preview route before the legacy storyteller prefix:

```js
if (hash.startsWith('#/storyteller-preview')) {
  return { vuePage: 'storyteller-preview' }
}
if (hash.startsWith('#/storyteller')) {
  return { legacyUrl: `/legacy/${hash}` }
}
```

Create the first `StorytellerPreviewPage.vue`:

```vue
<template>
  <main data-storyteller-preview class="page center">
    <h1>说书人桌面版预览</h1>
    <a class="btn" href="/legacy/#/storyteller">打开完整控制台</a>
  </main>
</template>
```

Update `App.vue` to keep `page = ref('loading')`, set `page.value` only after the route-version guard, render the preview for `storyteller-preview`, and render `JoinPage` for `join`.

- [ ] **Step 4: Run the route tests and the complete frontend suite**

Run: `npm --prefix frontend test -- --run tests/app-routing.test.js tests/app-preview-routing.test.js && npm --prefix frontend test`

Expected: route tests PASS and the complete suite PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.vue frontend/src/services/navigation.js frontend/src/pages/StorytellerPreviewPage.vue frontend/tests/app-routing.test.js frontend/tests/app-preview-routing.test.js
git commit -m "feat: add storyteller Vue preview route"
```

---

### Task 2: Add the Reconnecting WebSocket Transport

**Files:**
- Create: `frontend/src/services/websocket.js`
- Create: `frontend/tests/websocket.test.js`

**Interfaces:**
- Consumes: browser `location.protocol`, `location.host`, `WebSocket`, `setTimeout`, and `clearTimeout` through injectable defaults.
- Produces: `openSocket({ query, onMessage, onStatus, onFatal, WebSocketImpl, schedule, cancel }) -> { close() }`; status values are `connecting`, `connected`, and `reconnecting`.

- [ ] **Step 1: Write transport tests with a deterministic fake socket**

Create `frontend/tests/websocket.test.js` with this deterministic socket fake:

```js
class FakeSocket {
  static instances = []
  static reset() { FakeSocket.instances = [] }

  constructor(url) {
    this.url = url
    this.readyState = 0
    FakeSocket.instances.push(this)
  }

  emitOpen() {
    this.readyState = 1
    this.onopen?.()
  }

  emitMessage(value) {
    this.onmessage?.({ data: JSON.stringify(value) })
  }

  emitClose(code) {
    this.readyState = 3
    this.onclose?.({ code })
  }

  close() {
    this.readyState = 3
  }
}

beforeEach(() => FakeSocket.reset())
```

Pin these behaviors:

```js
it('parses messages and reports a connected socket', () => {
  const onMessage = vi.fn()
  const onStatus = vi.fn()
  openSocket({ query: 'who=storyteller&pw=secret', onMessage, onStatus, WebSocketImpl: FakeSocket })
  const socket = FakeSocket.instances[0]
  expect(socket.url).toContain('/ws?who=storyteller&pw=secret')
  socket.emitOpen()
  socket.emitMessage({ room_code: '2468' })
  expect(onStatus).toHaveBeenLastCalledWith('connected')
  expect(onMessage).toHaveBeenCalledWith({ room_code: '2468' })
})

it('keeps ownership alive and schedules one reconnect after a transient close', () => {
  let retry
  const schedule = vi.fn((fn) => { retry = fn; return 7 })
  const onFatal = vi.fn()
  openSocket({ query: 'who=storyteller', onMessage: vi.fn(), onStatus: vi.fn(), onFatal,
    WebSocketImpl: FakeSocket, schedule })
  FakeSocket.instances[0].emitClose(1006)
  expect(schedule).toHaveBeenCalledTimes(1)
  expect(onFatal).not.toHaveBeenCalled()
  retry()
  expect(FakeSocket.instances).toHaveLength(2)
})

it('treats authentication close as fatal without reconnecting', () => {
  const schedule = vi.fn()
  const onFatal = vi.fn()
  openSocket({ query: 'who=storyteller', onMessage: vi.fn(), onStatus: vi.fn(), onFatal,
    WebSocketImpl: FakeSocket, schedule })
  FakeSocket.instances[0].emitClose(4003)
  expect(onFatal).toHaveBeenCalledWith(4003)
  expect(schedule).not.toHaveBeenCalled()
})
```

- [ ] **Step 2: Run the transport tests and verify RED**

Run: `npm --prefix frontend test -- --run tests/websocket.test.js`

Expected: FAIL because `services/websocket.js` does not exist.

- [ ] **Step 3: Implement the transport**

Use this lifecycle in `openSocket`:

```js
export function openSocket({
  query,
  onMessage,
  onStatus = () => {},
  onFatal = () => {},
  WebSocketImpl = WebSocket,
  schedule = setTimeout,
  cancel = clearTimeout,
}) {
  let socket = null
  let retryTimer = null
  let stopped = false
  let attempts = 0

  const connect = () => {
    if (stopped) return
    onStatus(attempts ? 'reconnecting' : 'connecting')
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
    socket = new WebSocketImpl(`${protocol}://${location.host}/ws?${query}`)
    socket.onopen = () => { attempts = 0; onStatus('connected') }
    socket.onmessage = (event) => onMessage(JSON.parse(event.data))
    socket.onclose = (event) => {
      if (stopped) return
      if (event.code === 4001 || event.code === 4003) {
        stopped = true
        onFatal(event.code)
        return
      }
      attempts += 1
      onStatus('reconnecting')
      retryTimer = schedule(connect, Math.min(500 * (2 ** (attempts - 1)), 5000))
    }
  }

  connect()
  return {
    close() {
      stopped = true
      if (retryTimer !== null) cancel(retryTimer)
      if (socket && socket.readyState < 2) socket.close()
    },
  }
}
```

- [ ] **Step 4: Run the transport tests and complete frontend suite**

Run: `npm --prefix frontend test -- --run tests/websocket.test.js && npm --prefix frontend test`

Expected: all tests PASS with no unhandled timers or console errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/services/websocket.js frontend/tests/websocket.test.js
git commit -m "feat: add reconnecting WebSocket transport"
```

---

### Task 3: Add Storyteller Authentication and Live View Ownership

**Files:**
- Modify: `frontend/src/services/session.js`
- Create: `frontend/src/composables/useStorytellerView.js`
- Create: `frontend/src/components/storyteller/StorytellerLogin.vue`
- Create: `frontend/src/components/storyteller/StorytellerLiveView.vue`
- Modify: `frontend/src/pages/StorytellerPreviewPage.vue`
- Modify: `frontend/tests/session.test.js`
- Modify: `frontend/tests/app-preview-routing.test.js`
- Modify: `frontend/tests/app-hash-routing.test.js`
- Create: `frontend/tests/storyteller-login.test.js`
- Create: `frontend/tests/storyteller-view.test.js`

**Interfaces:**
- Consumes: `ST_PASSWORD_KEY`, `PLAYER_ID_KEY`, `api`, and `openSocket` from Task 2.
- Produces: `getStorytellerPassword()`, `setStorytellerPassword(password)`, `clearStorytellerPassword()`; `useStorytellerView(password, { onAuthFailure }) -> { view, connectionStatus }`; `StorytellerLogin` emits `authenticated(password)`.

- [ ] **Step 1: Extend the session test first**

Add assertions to `frontend/tests/session.test.js`:

```js
setStorytellerPassword('secret')
expect(getStorytellerPassword()).toBe('secret')
clearStorytellerPassword()
expect(getStorytellerPassword()).toBeNull()
```

- [ ] **Step 2: Write login and live-view failing tests**

In `storyteller-login.test.js`, mock `api` and session storage, submit `secret`, and assert:

```js
expect(api).toHaveBeenCalledWith('/api/login', {
  method: 'POST', body: JSON.stringify({ password: 'secret' }),
})
expect(setStorytellerPassword).toHaveBeenCalledWith('secret')
expect(wrapper.emitted('authenticated')).toEqual([['secret']])
```

Also reject `{ ok: false }` and assert visible `密码错误` plus an enabled submit button.

In `storyteller-view.test.js`, mock `openSocket`, capture its callbacks, and use a mounted harness around `useStorytellerView`. Assert that `onMessage(firstView)` sets the view, `onStatus('reconnecting')` retains that same view, and `onFatal(4003)` calls `clearStorytellerPassword` and the supplied `onAuthFailure` while `localStorage.getItem('botc_player_id')` remains unchanged.

- [ ] **Step 3: Run the focused tests and verify RED**

Run: `npm --prefix frontend test -- --run tests/session.test.js tests/storyteller-login.test.js tests/storyteller-view.test.js`

Expected: FAIL because the password helpers, login component, and composable do not exist.

- [ ] **Step 4: Implement authentication and view ownership**

Add password helpers beside the player helpers in `session.js`. Implement `StorytellerLogin.vue` with a password field, `进入魔典` submit button, pending state, and inline error.

Implement the composable with `shallowRef(null)` for `view`, `ref('connecting')` for status, one encoded query:

```js
const connection = openSocket({
  query: `who=storyteller&pw=${encodeURIComponent(password)}`,
  onMessage: (nextView) => { view.value = nextView },
  onStatus: (nextStatus) => { connectionStatus.value = nextStatus },
  onFatal: () => {
    clearStorytellerPassword()
    onAuthFailure()
  },
})
```

Close the connection in `onBeforeUnmount`.

Update the session mocks in `app-preview-routing.test.js` and `app-hash-routing.test.js` with these exports so the complete suite can load the new page:

```js
getStorytellerPassword: vi.fn().mockReturnValue(null),
setStorytellerPassword: vi.fn(),
clearStorytellerPassword: vi.fn(),
```

`StorytellerPreviewPage.vue` owns `password = ref(getStorytellerPassword())`, renders `StorytellerLogin` when it is empty, and renders a keyed `StorytellerLiveView` after the `authenticated(password)` event. `StorytellerLiveView.vue` calls `useStorytellerView` unconditionally during setup and renders `连接魔典…` until the first projection arrives. Its `onAuthFailure` emit returns the parent to the login component. This explicit child boundary prevents conditional composable lifecycle registration.

- [ ] **Step 5: Run focused tests and the complete frontend suite**

Run: `npm --prefix frontend test -- --run tests/session.test.js tests/storyteller-login.test.js tests/storyteller-view.test.js && npm --prefix frontend test`

Expected: all tests PASS; the fatal-auth test preserves `botc_player_id`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/services/session.js frontend/src/composables/useStorytellerView.js frontend/src/components/storyteller/StorytellerLogin.vue frontend/src/components/storyteller/StorytellerLiveView.vue frontend/src/pages/StorytellerPreviewPage.vue frontend/tests/session.test.js frontend/tests/app-preview-routing.test.js frontend/tests/app-hash-routing.test.js frontend/tests/storyteller-login.test.js frontend/tests/storyteller-view.test.js
git commit -m "feat: connect storyteller preview to live view"
```

---

### Task 4: Build the Fixed Desktop Shell and Header

**Files:**
- Create: `frontend/tests/fixtures/storytellerView.js`
- Create: `frontend/src/presentation/storyteller.js`
- Create: `frontend/src/components/storyteller/StorytellerShell.vue`
- Create: `frontend/src/components/storyteller/StorytellerHeader.vue`
- Create: `frontend/src/components/storyteller/GameControlPanel.vue`
- Create: `frontend/src/styles/storyteller.css`
- Modify: `frontend/src/components/storyteller/StorytellerLiveView.vue`
- Create: `frontend/tests/storyteller-shell.test.js`

**Interfaces:**
- Consumes: live storyteller projection fields `status`, `phase`, `night_no`, `day_no`, `day_stage`, `room_code`, `script`, `scripts`, `player_count`, and `seats`.
- Produces: `getPhaseLabel(view) -> string`; `StorytellerShell` slots/regions `header`, `controls`, `board`, and `context`; events `open-left`, `open-right`, and `close-drawer` for narrow-window drawers.

- [ ] **Step 1: Create the shared fixture and failing presentation tests**

Create `storytellerView.js` with a six-seat lobby projection, including script metadata and two joined players. In `storyteller-shell.test.js`, assert:

```js
expect(getPhaseLabel(lobbyView)).toBe('等待开局')
expect(getPhaseLabel({ ...lobbyView, status: 'playing', phase: 'night', night_no: 2 }))
  .toBe('第 2 夜')
expect(getPhaseLabel({ ...lobbyView, status: 'playing', phase: 'day', day_no: 1,
  day_stage: 'nom' })).toBe('第 1 天 · 提名')
```

Mount the shell and assert one each of `[data-shell-header]`, `[data-shell-controls]`, `[data-shell-board]`, and `[data-shell-context]`. Mount the header and assert room code, script name, phase label, connection state, and a link whose `href` is `/legacy/#/storyteller`.

- [ ] **Step 2: Run shell tests and verify RED**

Run: `npm --prefix frontend test -- --run tests/storyteller-shell.test.js`

Expected: FAIL because the fixture, presentation helper, and components do not exist.

- [ ] **Step 3: Implement the shell and header**

Implement `getPhaseLabel` as a pure function with explicit mappings for `talk`, `nom`, and `vote`. Build the shell with semantic `header`, `aside`, `section`, and `aside` elements.

`StorytellerHeader` displays state and connection status, exposes left/right drawer buttons below 1180 px, and uses `打开完整控制台` as this preview slice's only primary action. `GameControlPanel` displays read-only script, player count, seating count, and a collapsed explanation that setup controls are still available in the complete console.

Add `storyteller.css` with these exact layout rules:

```css
.storyteller-shell { height: 100dvh; overflow: hidden; display: grid; grid-template-rows: 64px 1fr; }
.storyteller-grid { min-height: 0; padding: 16px; display: grid; gap: 16px; grid-template-columns: 260px minmax(560px, 1fr) 320px; }
.storyteller-panel { min-height: 0; border: 1px solid var(--line); border-radius: 16px; background: var(--panel); }
.storyteller-controls, .storyteller-context { overflow: auto; }
.storyteller-board { overflow: hidden; }
body:has(.storyteller-shell) { overflow: hidden; }
```

At `max-width: 1179px`, make the center column full width and position side panels as fixed drawers controlled by component classes. Import the stylesheet from `StorytellerLiveView.vue`, which renders `StorytellerShell` after the first projection arrives.

- [ ] **Step 4: Run shell tests and the complete frontend suite**

Run: `npm --prefix frontend test -- --run tests/storyteller-shell.test.js && npm --prefix frontend test`

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/tests/fixtures/storytellerView.js frontend/src/presentation/storyteller.js frontend/src/components/storyteller/StorytellerShell.vue frontend/src/components/storyteller/StorytellerHeader.vue frontend/src/components/storyteller/GameControlPanel.vue frontend/src/styles/storyteller.css frontend/src/components/storyteller/StorytellerLiveView.vue frontend/tests/storyteller-shell.test.js
git commit -m "feat: build storyteller desktop shell"
```

---

### Task 5: Add the Read-Only Grimoire Board

**Files:**
- Create: `frontend/src/components/storyteller/SeatNode.vue`
- Create: `frontend/src/components/storyteller/GrimoireBoard.vue`
- Modify: `frontend/src/components/storyteller/StorytellerLiveView.vue`
- Create: `frontend/tests/grimoire-board.test.js`

**Interfaces:**
- Consumes: `seats: Array<{ seat, player, assigned_role?, dead_vote_left?, markers?, role_change?, team_change? }>` and `selectedSeat: number|null`.
- Produces: `GrimoireBoard` event `select-seat(seatNumber)`; seat CSS variables `--seat-x` and `--seat-y`; accessible button names containing seat number and player/empty state.

- [ ] **Step 1: Write the failing board tests**

Create `grimoire-board.test.js` and mount six seats from the fixture. Assert six seat buttons, an accessible `1号 · 阿青` label, an empty `3号 · 空座` label, and:

```js
await wrapper.get('[data-seat="1"]').trigger('click')
expect(wrapper.emitted('select-seat')).toEqual([[1]])
expect(wrapper.get('[data-seat="2"]').attributes('style')).toContain('--seat-x:')
expect(wrapper.get('[data-seat="2"]').attributes('style')).toContain('--seat-y:')
```

Mount a dead player with `markers: ['poisoned']` and assert visible `死亡` and `中毒` text, so marker meaning does not depend on color.

- [ ] **Step 2: Run the board test and verify RED**

Run: `npm --prefix frontend test -- --run tests/grimoire-board.test.js`

Expected: FAIL because `GrimoireBoard.vue` and `SeatNode.vue` do not exist.

- [ ] **Step 3: Implement seat geometry and visual state**

In `GrimoireBoard`, calculate each angle with:

```js
const angle = ((2 * Math.PI) / seats.length) * (seat.seat - 1) - (Math.PI / 2)
const position = {
  '--seat-x': `${50 + 40 * Math.cos(angle)}%`,
  '--seat-y': `${50 + 40 * Math.sin(angle)}%`,
}
```

Render `SeatNode` as a real button positioned with those variables. Show role/team to the storyteller when present, life state, and compact text marker badges. Use separate `is-selected` and `is-contextual` classes. Add a centered non-interactive storyteller candle.

Size the board with `width: min(100%, 650px); aspect-ratio: 1; max-height: calc(100dvh - 128px)` and center it inside the middle panel.

- [ ] **Step 4: Run focused and complete tests**

Run: `npm --prefix frontend test -- --run tests/grimoire-board.test.js && npm --prefix frontend test`

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/storyteller/SeatNode.vue frontend/src/components/storyteller/GrimoireBoard.vue frontend/src/components/storyteller/StorytellerLiveView.vue frontend/src/styles/storyteller.css frontend/tests/grimoire-board.test.js
git commit -m "feat: add Vue storyteller grimoire board"
```

---

### Task 6: Add Join Context and Selection-Safe Player Details

**Files:**
- Create: `frontend/src/components/storyteller/JoinPanel.vue`
- Create: `frontend/src/components/storyteller/PlayerDetailPanel.vue`
- Create: `frontend/src/components/storyteller/ContextPanel.vue`
- Modify: `frontend/src/components/storyteller/StorytellerLiveView.vue`
- Create: `frontend/tests/storyteller-context.test.js`

**Interfaces:**
- Consumes: storyteller fields `room_code`, `seats`, `players`, `status`; local `selectedSeat`.
- Produces: context event `clear-selection`; `JoinPanel` QR source `/api/qr`; automatic selected-seat clearing when the next server view no longer contains that player.

- [ ] **Step 1: Write failing context-priority tests**

In `storyteller-context.test.js`, mount `ContextPanel` with no selection and assert room code, `/api/qr`, and `已入座 2/6`. Mount it with selected seat 1 and assert player name, role, team, life state, markers, and no QR image. Click close and assert `clear-selection`.

Mount `StorytellerLiveView` with the view composable mocked as a writable shallow ref. Select seat 1, replace the view with a projection where seat 1 has no player, await the update, and assert the join panel is restored and the removed player's name is absent.

- [ ] **Step 2: Run the context tests and verify RED**

Run: `npm --prefix frontend test -- --run tests/storyteller-context.test.js`

Expected: FAIL because context components and selection invalidation do not exist.

- [ ] **Step 3: Implement context priority and stale-selection clearing**

`ContextPanel` renders `PlayerDetailPanel` when `selectedSeat` resolves to a current player; otherwise it renders `JoinPanel`. `PlayerDetailPanel` is read-only in this slice and includes an `返回当前任务` close button plus `在完整控制台中操作` link.

In `StorytellerLiveView`, own `selectedSeat = ref(null)`. Watch the live projection's seats and clear selection when:

```js
const selected = nextSeats.find((seat) => seat.seat === selectedSeat.value)
if (!selected?.player) selectedSeat.value = null
```

Wire `GrimoireBoard` selection to the context panel and drawer state. The default lobby context remains join/QR information.

- [ ] **Step 4: Run focused and complete frontend tests**

Run: `npm --prefix frontend test -- --run tests/storyteller-context.test.js && npm --prefix frontend test`

Expected: all tests PASS, including the removed-player privacy case.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/storyteller/JoinPanel.vue frontend/src/components/storyteller/PlayerDetailPanel.vue frontend/src/components/storyteller/ContextPanel.vue frontend/src/components/storyteller/StorytellerLiveView.vue frontend/tests/storyteller-context.test.js
git commit -m "feat: add storyteller context panels"
```

---

### Task 7: Build, Document, and Verify the Preview End to End

**Files:**
- Modify: `docs/migration/vue-vite-status.md`
- Modify: `README.md`
- Modify: `frontend/dist/**`

**Interfaces:**
- Consumes: complete preview route and components from Tasks 1-6.
- Produces: committed Vite bundle, documented preview URL, and acceptance evidence at 1366x768 and a larger desktop viewport.

- [ ] **Step 1: Update migration documentation**

Document that:

- `/#/storyteller` remains the complete legacy console;
- `/#/storyteller-preview` is the Vue read-only migration preview;
- setup and live-game mutations continue through the visible `打开完整控制台` link;
- this slice completes desktop shell, live grimoire, join context, and player inspection only.

- [ ] **Step 2: Run fresh dependency, test, and build verification**

Run:

```bash
npm --prefix frontend ci
npm --prefix frontend test
npm --prefix frontend run build
```

Expected: clean install succeeds, every frontend test passes, and Vite creates `frontend/dist/index.html` plus hashed assets.

- [ ] **Step 3: Run backend compatibility verification**

Run:

```bash
env PYTHONPATH=backend /Users/lichenxi/botc-grimoire/backend/.venv/bin/python -m unittest discover -s backend/tests -v
/Users/lichenxi/botc-grimoire/backend/.venv/bin/python -m compileall -q backend
```

Start the isolated test server if it is not already running, then run:

```bash
env -u ALL_PROXY -u all_proxy -u HTTP_PROXY -u http_proxy -u HTTPS_PROXY -u https_proxy \
  NO_PROXY=localhost,127.0.0.1 no_proxy=localhost,127.0.0.1 \
  SMOKE_BASE=http://localhost:8001 \
  /Users/lichenxi/botc-grimoire/backend/.venv/bin/python backend/smoke_test.py
```

Expected: backend unit tests report `OK`, compilation exits zero, and smoke output ends with `ALL PASS`.

- [ ] **Step 4: Perform browser acceptance at exact desktop sizes**

Open `http://localhost:8001/#/storyteller-preview`, authenticate with the configured local storyteller password, and check both `1366x768` and `1600x900`:

- `document.documentElement.scrollHeight === document.documentElement.clientHeight`;
- `document.documentElement.scrollWidth === document.documentElement.clientWidth`;
- header, whole board, and right-panel heading are visible;
- QR and room code are visible in the lobby default context;
- selecting a player changes only the right panel;
- the complete-console link reaches `/legacy/#/storyteller`;
- direct `/#/storyteller` still redirects to legacy;
- browser console has no errors.

At 1100 px width, verify both side-panel drawer buttons open and close their respective panels without covering the header.

- [ ] **Step 5: Commit documentation and production bundle**

```bash
git add README.md docs/migration/vue-vite-status.md frontend/dist
git commit -m "docs: publish storyteller Vue preview"
```

- [ ] **Step 6: Run final clean-tree verification**

Run:

```bash
git diff --check
git status --short
```

Expected: `git diff --check` exits zero and `git status --short` is empty.

---

## Follow-up Plans

After this plan is accepted, use separate plans for:

1. lobby setup, manual/random assignment, fabled roles, Sentinel, and start controls;
2. selected-player mutations, phase controls, and night workflow;
3. nominations, voting, travelers, chat supervision, ending, and review;
4. final storyteller route cutover and legacy storyteller removal.

Each follow-up keeps the production storyteller route on legacy until its complete workflow is present and independently verified.
