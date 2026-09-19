# Vue/Vite Shell and Join Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a production-buildable Vue 3/Vite frontend and migrate the join page while keeping the existing player and storyteller interfaces available through a same-origin legacy route.

**Architecture:** Vite builds `frontend/src/` into `frontend/dist/`, which FastAPI serves at `/`. The existing zero-build frontend moves to `frontend/legacy/` and remains available at `/legacy/`; Vue redirects returning players and storyteller routes there until their dedicated migration plans are complete. Shared REST, session, and route-selection behavior lives outside Vue components so it can be tested independently and reused by later migrations.

**Tech Stack:** Vue 3, Vite, Vitest, Vue Test Utils, jsdom, FastAPI, Python 3.12

**Spec:** `docs/superpowers/specs/2026-09-20-vue-vite-modular-migration-design.md`

## Global Constraints

- Preserve all existing REST URLs, request bodies, response bodies, and WebSocket message structures.
- Preserve compatibility with `backend/data/game.json`.
- Preserve the single-table, single-process, LAN-first runtime model.
- Keep the legacy frontend available as a rollback path until player and storyteller migrations are complete.
- Do not add a database, multi-room support, microservices, TypeScript conversion, or new game behavior.
- Commit `frontend/package-lock.json`; production must not need Node, npm, or internet access after `npm run build`.

## Review Focus

- A stale player id in local storage must be cleared and must return the user to the Vue join page instead of causing a redirect loop; pinned in Task 4.
- A valid returning player must reach the legacy player page without losing same-origin local storage; pinned in Task 4.
- `/#/storyteller` must preserve the hash while redirecting to `/legacy/#/storyteller`; pinned in Task 4.
- FastAPI must still serve API and WebSocket routes before the root static mount; pinned by the complete backend smoke test in Task 5.
- A missing `frontend/dist/` in a source checkout must produce an actionable startup error rather than silently serving a half-migrated application; pinned in Task 5.

---

## Planned File Structure

```text
frontend/
  package.json                 npm scripts and pinned direct dependencies
  package-lock.json            reproducible dependency resolution
  vite.config.js               Vue plugin, build output, dev API/WS proxy
  index.html                   Vite HTML entry
  src/
    main.js                    Vue bootstrap
    App.vue                    route selection and legacy handoff
    constants.js               local-storage keys shared by pages/services
    services/
      api.js                   JSON request/error normalization
      session.js               player-id storage access
    pages/
      JoinPage.vue             room/name form and join workflow
    styles/
      tokens.css               colors, spacing, typography variables
      base.css                 document and shared form/button styling
  tests/
    setup.js                   Vue test cleanup
    api.test.js                REST error normalization tests
    session.test.js            local-storage contract tests
    app-routing.test.js        legacy handoff tests
    join-page.test.js          join form interaction tests
  legacy/
    index.html                 existing zero-build entry
    app.js                     existing player/storyteller implementation
    styles.css                 existing styles
backend/app/main.py            serve dist root and legacy fallback route
README.md                      development/build/production instructions
```

### Task 1: Establish the Vue/Vite Testable Shell

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/src/main.js`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/styles/tokens.css`
- Create: `frontend/src/styles/base.css`
- Create: `frontend/tests/setup.js`
- Create: `frontend/tests/app-shell.test.js`
- Modify: `frontend/index.html`

**Interfaces:**
- Consumes: no application interfaces; this is the frontend build foundation.
- Produces: `npm run dev`, `npm run build`, `npm test`, and a Vue root component mounted at `#app`.

- [ ] **Step 1: Create the npm manifest and install locked dependencies**

Create `frontend/package.json` with this initial content:

```json
{
  "name": "botc-grimoire-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "test": "vitest run",
    "test:watch": "vitest"
  }
}
```

Run:

```bash
cd frontend
npm install vue
npm install --save-dev vite @vitejs/plugin-vue vitest @vue/test-utils jsdom
```

Expected: `package.json` contains direct dependency versions and `package-lock.json` is created.

- [ ] **Step 2: Write the failing shell test**

Create `frontend/tests/setup.js`:

```js
import { afterEach } from 'vitest'
import { enableAutoUnmount } from '@vue/test-utils'

enableAutoUnmount(afterEach)
```

Create `frontend/tests/app-shell.test.js`:

```js
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import App from '../src/App.vue'

describe('App shell', () => {
  it('mounts a page container', () => {
    const wrapper = mount(App)
    expect(wrapper.get('[data-app-shell]').exists()).toBe(true)
  })
})
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `cd frontend && npm test -- app-shell.test.js`

Expected: FAIL because `src/App.vue` does not exist.

- [ ] **Step 4: Implement the minimal Vue shell and Vite configuration**

Create `frontend/vite.config.js`:

```js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./tests/setup.js'],
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/ws': { target: 'ws://127.0.0.1:8000', ws: true },
      '/legacy': 'http://127.0.0.1:8000',
    },
  },
})
```

Create `frontend/src/App.vue`:

```vue
<template>
  <main data-app-shell class="page center">
    <p>加载中…</p>
  </main>
</template>
```

Create `frontend/src/main.js`:

```js
import { createApp } from 'vue'
import App from './App.vue'
import './styles/tokens.css'
import './styles/base.css'

createApp(App).mount('#app')
```

Replace `frontend/index.html` with a Vite entry that retains the current title, viewport, favicon, and `#app`, and loads `/src/main.js` as a module.

Create `tokens.css` with the existing page background, text, primary, error, border, and spacing values extracted from `frontend/styles.css`. Create `base.css` with `box-sizing`, body, `.page`, `.center`, `.input`, `.btn`, `.primary`, `.hint`, and `.error` rules copied without visual changes.

- [ ] **Step 5: Run tests and production build**

Run:

```bash
cd frontend
npm test
npm run build
```

Expected: one test passes and `frontend/dist/index.html` exists.

- [ ] **Step 6: Commit the shell**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.js frontend/index.html frontend/src frontend/tests
git commit -m "build: add Vue and Vite frontend shell"
```

### Task 2: Add Tested REST and Session Services

**Files:**
- Create: `frontend/src/constants.js`
- Create: `frontend/src/services/api.js`
- Create: `frontend/src/services/session.js`
- Create: `frontend/tests/api.test.js`
- Create: `frontend/tests/session.test.js`

**Interfaces:**
- Consumes: browser `fetch` and `localStorage`.
- Produces: `api(path, init): Promise<object>`, `getPlayerId(): string | null`, `setPlayerId(id): void`, and `clearPlayerId(): void`.

- [ ] **Step 1: Write failing API normalization tests**

Create `frontend/tests/api.test.js`:

```js
import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from '../src/services/api.js'

afterEach(() => vi.unstubAllGlobals())

describe('api', () => {
  it('merges JSON and caller headers', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true }),
    })
    vi.stubGlobal('fetch', fetchMock)
    await api('/api/state', { headers: { 'X-Storyteller-Password': 'secret' } })
    expect(fetchMock.mock.calls[0][1].headers).toEqual({
      'Content-Type': 'application/json',
      'X-Storyteller-Password': 'secret',
    })
  })

  it('formats FastAPI 422 errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: [{ loc: ['body', 'room_code'], msg: 'invalid' }] }),
    }))
    await expect(api('/api/join')).rejects.toThrow('body.room_code: invalid')
  })

  it('falls back to the HTTP status for non-JSON errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => { throw new Error('not json') },
    }))
    await expect(api('/api/info')).rejects.toThrow('HTTP 503')
  })
})
```

- [ ] **Step 2: Write failing session tests**

Create `frontend/tests/session.test.js`:

```js
import { beforeEach, describe, expect, it } from 'vitest'
import { clearPlayerId, getPlayerId, setPlayerId } from '../src/services/session.js'

beforeEach(() => localStorage.clear())

describe('player session', () => {
  it('stores, reads, and clears the player id', () => {
    expect(getPlayerId()).toBeNull()
    setPlayerId('abc123')
    expect(getPlayerId()).toBe('abc123')
    clearPlayerId()
    expect(getPlayerId()).toBeNull()
  })
})
```

- [ ] **Step 3: Run both tests to verify they fail**

Run: `cd frontend && npm test -- api.test.js session.test.js`

Expected: FAIL because the service modules do not exist.

- [ ] **Step 4: Implement the shared services**

Create `frontend/src/constants.js`:

```js
export const PLAYER_ID_KEY = 'botc_player_id'
export const ST_PASSWORD_KEY = 'botc_st_password'
```

Create `frontend/src/services/session.js`:

```js
import { PLAYER_ID_KEY } from '../constants.js'

export const getPlayerId = () => localStorage.getItem(PLAYER_ID_KEY)
export const setPlayerId = (id) => localStorage.setItem(PLAYER_ID_KEY, id)
export const clearPlayerId = () => localStorage.removeItem(PLAYER_ID_KEY)
```

Create `frontend/src/services/api.js` by moving the behavior of the current `api()` function unchanged: merge `Content-Type` after spreading `init`, parse JSON, format array-shaped FastAPI validation details as `location: message`, and throw `HTTP <status>` when no detail exists.

- [ ] **Step 5: Run service tests**

Run: `cd frontend && npm test -- api.test.js session.test.js`

Expected: six assertions pass across four tests.

- [ ] **Step 6: Commit the services**

```bash
git add frontend/src/constants.js frontend/src/services frontend/tests/api.test.js frontend/tests/session.test.js
git commit -m "refactor: extract frontend API and session services"
```

### Task 3: Migrate the Join Page

**Files:**
- Create: `frontend/src/pages/JoinPage.vue`
- Create: `frontend/tests/join-page.test.js`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/styles/base.css`

**Interfaces:**
- Consumes: `api('/api/join', { method: 'POST', body })` and `setPlayerId(id)` from Task 2.
- Produces: `joined` event with the new player id; exact form behavior and validation equivalent to the current `renderJoin()`.

- [ ] **Step 1: Write failing join-page interaction tests**

Create `frontend/tests/join-page.test.js` with mocked service modules:

```js
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import JoinPage from '../src/pages/JoinPage.vue'
import { api } from '../src/services/api.js'
import { setPlayerId } from '../src/services/session.js'

vi.mock('../src/services/api.js', () => ({ api: vi.fn() }))
vi.mock('../src/services/session.js', () => ({ setPlayerId: vi.fn() }))

beforeEach(() => {
  vi.clearAllMocks()
  window.location.hash = '#/?room=2468'
})

describe('JoinPage', () => {
  it('prefills the room from the QR hash', () => {
    const wrapper = mount(JoinPage)
    expect(wrapper.get('[data-room]').element.value).toBe('2468')
  })

  it('rejects a room code that is not four digits', async () => {
    const wrapper = mount(JoinPage)
    await wrapper.get('[data-name]').setValue('小明')
    await wrapper.get('[data-room]').setValue('12')
    await wrapper.get('form').trigger('submit')
    expect(wrapper.get('[data-error]').text()).toBe('房间号需为 4 位数字')
    expect(api).not.toHaveBeenCalled()
  })

  it('joins, stores the player id, and emits joined', async () => {
    api.mockResolvedValue({ player_id: 'player-token' })
    const wrapper = mount(JoinPage)
    await wrapper.get('[data-name]').setValue('小明')
    await wrapper.get('[data-room]').setValue('2468')
    await wrapper.get('form').trigger('submit')
    await vi.waitFor(() => expect(setPlayerId).toHaveBeenCalledWith('player-token'))
    expect(wrapper.emitted('joined')).toEqual([['player-token']])
  })

  it('shows the server error and re-enables submit', async () => {
    api.mockRejectedValue(new Error('房间号错误'))
    const wrapper = mount(JoinPage)
    await wrapper.get('[data-name]').setValue('小明')
    await wrapper.get('[data-room]').setValue('2468')
    await wrapper.get('form').trigger('submit')
    await vi.waitFor(() => expect(wrapper.get('[data-error]').text()).toBe('房间号错误'))
    expect(wrapper.get('[data-submit]').attributes('disabled')).toBeUndefined()
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npm test -- join-page.test.js`

Expected: FAIL because `JoinPage.vue` does not exist.

- [ ] **Step 3: Implement the join component**

Create `JoinPage.vue` using `<script setup>` with `ref` values for `name`, `roomCode`, `error`, and `submitting`. Parse the room code from `location.hash.split('?')[1]`, validate `/^\d{4}$/`, call the Task 2 API service, persist the id, and emit `joined`.

The template must use a semantic `<form @submit.prevent="join">`, preserve current Chinese copy, retain `maxlength`/`inputmode`, and expose the `data-name`, `data-room`, `data-submit`, and `data-error` selectors used by the test. Render the existing credit line as ordinary Vue template text rather than `v-html`.

Modify `App.vue` to render `<JoinPage @joined="onJoined" />`; for now `onJoined` assigns `location.href = '/legacy/'`.

- [ ] **Step 4: Run join and complete frontend tests**

Run:

```bash
cd frontend
npm test -- join-page.test.js
npm test
npm run build
```

Expected: all tests pass and the production build completes.

- [ ] **Step 5: Commit the join page**

```bash
git add frontend/src/App.vue frontend/src/pages/JoinPage.vue frontend/src/styles/base.css frontend/tests/join-page.test.js
git commit -m "feat: migrate join page to Vue"
```

### Task 4: Add Tested Legacy Handoff

**Files:**
- Create: `frontend/src/services/navigation.js`
- Create: `frontend/tests/app-routing.test.js`
- Modify: `frontend/src/App.vue`
- Move: `frontend/app.js` to `frontend/legacy/app.js`
- Move: `frontend/styles.css` to `frontend/legacy/styles.css`
- Create: `frontend/legacy/index.html` from the pre-migration `frontend/index.html`

**Interfaces:**
- Consumes: `getPlayerId()`, `clearPlayerId()`, and `api('/api/me/<id>')`.
- Produces: `resolveEntry(): Promise<'join' | { legacyUrl: string }>` and `goToLegacy(url): void`.

- [ ] **Step 1: Write failing route-selection tests**

Create `frontend/tests/app-routing.test.js` around a pure exported `resolveEntry({ hash, playerId, validatePlayer })` function:

```js
import { describe, expect, it, vi } from 'vitest'
import { resolveEntry } from '../src/services/navigation.js'

describe('entry routing', () => {
  it('preserves the storyteller hash', async () => {
    await expect(resolveEntry({
      hash: '#/storyteller', playerId: null, validatePlayer: vi.fn(),
    })).resolves.toEqual({ legacyUrl: '/legacy/#/storyteller' })
  })

  it('sends a valid returning player to legacy', async () => {
    const validatePlayer = vi.fn().mockResolvedValue({})
    await expect(resolveEntry({ hash: '', playerId: 'p1', validatePlayer }))
      .resolves.toEqual({ legacyUrl: '/legacy/' })
    expect(validatePlayer).toHaveBeenCalledWith('p1')
  })

  it('returns stale players to join', async () => {
    const validatePlayer = vi.fn().mockRejectedValue(new Error('gone'))
    await expect(resolveEntry({ hash: '', playerId: 'stale', validatePlayer }))
      .resolves.toBe('join')
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npm test -- app-routing.test.js`

Expected: FAIL because `navigation.js` does not exist.

- [ ] **Step 3: Implement route selection and App integration**

Implement `resolveEntry` exactly as tested. In `App.vue`, call it from `onMounted`; use `api(`/api/me/${encodeURIComponent(id)}`)` as `validatePlayer`. If validation fails, call `clearPlayerId()` before displaying `JoinPage`. Use `location.replace(legacyUrl)` for legacy handoff so browser Back does not create a redirect loop.

- [ ] **Step 4: Move legacy assets without altering their contents**

Use `git mv` for `app.js` and `styles.css`. Build `frontend/legacy/index.html` from the pre-migration entry and change only asset URLs to `/legacy/styles.css?v=4` and `/legacy/app.js?v=4`.

Verify exact preservation:

```bash
git show HEAD:frontend/app.js > /tmp/botc-app-before.js
cmp /tmp/botc-app-before.js frontend/legacy/app.js
git show HEAD:frontend/styles.css > /tmp/botc-styles-before.css
cmp /tmp/botc-styles-before.css frontend/legacy/styles.css
```

Expected: both `cmp` commands exit 0.

- [ ] **Step 5: Run routing tests and build**

Run:

```bash
cd frontend
npm test -- app-routing.test.js
npm test
npm run build
```

Expected: all tests and build pass.

- [ ] **Step 6: Commit legacy handoff**

```bash
git add frontend/src frontend/tests frontend/legacy
git commit -m "refactor: route unmigrated pages through legacy frontend"
```

### Task 5: Serve Vite Output and Preserve Backend Routes

**Files:**
- Create: `backend/tests/test_frontend_static.py`
- Create: `backend/tests/__init__.py`
- Modify: `backend/app/main.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `frontend/dist/` and `frontend/legacy/` produced by earlier tasks.
- Produces: Vue application at `/`, legacy application at `/legacy/`, unchanged `/api/*`, `/ws`, `/app.js`, and `/styles.css` compatibility routes during migration.

- [ ] **Step 1: Write the failing static-layout test**

Create a standard-library test that does not start the server:

Create an empty `backend/tests/__init__.py`, then create:

```python
from pathlib import Path
import unittest

from app.main import FRONTEND_DIST, FRONTEND_LEGACY


class FrontendStaticLayoutTest(unittest.TestCase):
    def test_built_and_legacy_entries_exist(self):
        self.assertEqual(FRONTEND_DIST.name, "dist")
        self.assertEqual(FRONTEND_LEGACY.name, "legacy")
        self.assertTrue((FRONTEND_DIST / "index.html").is_file())
        self.assertTrue((FRONTEND_LEGACY / "index.html").is_file())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && .venv/bin/python -m unittest tests.test_frontend_static -v`

Expected: FAIL because the exported path constants do not exist.

- [ ] **Step 3: Implement explicit static mounts**

In `backend/app/main.py`, replace `_FRONTEND` with exported constants:

```python
FRONTEND_ROOT = Path(__file__).resolve().parent.parent.parent / "frontend"
FRONTEND_DIST = FRONTEND_ROOT / "dist"
FRONTEND_LEGACY = FRONTEND_ROOT / "legacy"

if not (FRONTEND_DIST / "index.html").is_file():
    raise RuntimeError(
        "frontend/dist is missing; run `cd frontend && npm install && npm run build`"
    )
```

Keep existing `/app.js` and `/styles.css` compatibility handlers, but point them to legacy files. Mount legacy before root:

```python
app.mount("/legacy", StaticFiles(directory=str(FRONTEND_LEGACY), html=True), name="legacy")
app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
```

Do not move the root mount above API or WebSocket route declarations.

- [ ] **Step 4: Make build artifacts an intentional deployment choice**

Do not ignore `frontend/dist/`; commit it because production is Python-only. Remove the current generic `dist/` ignore entry. Keep the existing `node_modules/` and `.vite/` entries, which already cover frontend dependencies and Vite's transient cache.

- [ ] **Step 5: Run backend layout and compile tests**

Run:

```bash
cd backend
.venv/bin/python -m unittest tests.test_frontend_static -v
.venv/bin/python -m compileall -q app tests smoke_test.py
```

Expected: static-layout test passes and compileall exits 0.

- [ ] **Step 6: Run the complete isolated smoke test**

Terminal A:

```bash
cd backend
.venv/bin/python tools/run_test_server.py
```

Terminal B:

```bash
cd backend
NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost \
  SMOKE_BASE=http://127.0.0.1:8001 .venv/bin/python smoke_test.py
```

Expected: final line `ALL PASS`.

- [ ] **Step 7: Commit production serving**

```bash
git add .gitignore backend/app/main.py backend/tests/__init__.py backend/tests/test_frontend_static.py frontend/dist
git commit -m "build: serve Vue build with legacy fallback"
```

### Task 6: Document and Manually Verify the Milestone

**Files:**
- Modify: `README.md`
- Create: `docs/migration/vue-vite-status.md`

**Interfaces:**
- Consumes: all deliverables from Tasks 1-5.
- Produces: reproducible developer and production instructions plus a migration status record for the next plan.

- [ ] **Step 1: Update README commands**

Document these exact flows:

```bash
# Frontend development
cd frontend
npm install
npm run dev

# Production frontend build
cd frontend
npm ci
npm test
npm run build

# Production server
cd backend
.venv/bin/python run.py
```

State explicitly that Node is needed only to develop/build the frontend; the committed `frontend/dist/` lets the production FastAPI server run without Node or internet access.

- [ ] **Step 2: Record migration state**

Create `docs/migration/vue-vite-status.md` with a checked list stating:

```markdown
- [x] Vue/Vite production shell
- [x] Shared REST and session services
- [x] Join page migrated
- [ ] Player page migrated
- [ ] Storyteller page migrated
- [ ] Legacy frontend removed
- [ ] Backend routers and domains modularized
```

Document that `/legacy/` is temporary and identify `6cc6479` as the pre-migration functional baseline.

- [ ] **Step 3: Run the full verification matrix**

Run:

```bash
cd frontend && npm ci && npm test && npm run build
cd ../backend && .venv/bin/python -m unittest tests.test_frontend_static -v
.venv/bin/python -m compileall -q app tests smoke_test.py
```

Then run the isolated `smoke_test.py` procedure from Task 5 and verify `ALL PASS`.

- [ ] **Step 4: Perform browser checks**

Using the isolated server, verify:

1. `/` displays the Vue join page at desktop and 390px mobile width.
2. A QR-style `/#/?room=1234` URL prefills the room field.
3. Successful join stores the player id and reaches `/legacy/` with the existing player UI.
4. Refreshing `/` with a valid stored player reaches `/legacy/`.
5. A stale stored player id is cleared and displays the join page.
6. `/#/storyteller` reaches `/legacy/#/storyteller` and the existing login works.
7. Browser console has no uncaught errors during these flows.

- [ ] **Step 5: Commit documentation and milestone status**

```bash
git add README.md docs/migration/vue-vite-status.md frontend/dist
git commit -m "docs: document Vue Vite development and migration status"
```

## Follow-up Plans

After this plan passes review and verification, write and execute separate implementation plans in this order:

1. `Vue Player Page Migration` — seat circle, role card, nominations, night actions, chat, settlement.
2. `Vue Storyteller Page Migration` — configuration, assignment, night flow, travelers, chat oversight, review.
3. `FastAPI Modular Monolith Refactor` — routers, realtime hub, persistence, projections, then domain modules.

Each follow-up must preserve the interfaces established in this plan and must finish with the existing complete smoke test.
