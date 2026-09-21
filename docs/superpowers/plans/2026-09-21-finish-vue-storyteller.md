# Finish Vue Storyteller Administration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the remaining legacy storyteller controls with focused Vue components and the existing REST contract.

**Architecture:** `StorytellerLiveView` owns server view and command execution. Focused traveler, chat, game administration, review, and seat components receive props and emit intent. The existing `createStorytellerService` sends the exact legacy API payloads. No rule or save-format changes.

**Tech Stack:** Vue 3, Vite, Vitest, Vue Test Utils, FastAPI.

**Spec:** `docs/superpowers/specs/2026-09-20-vue-vite-modular-migration-design.md`

## Global Constraints

- Preserve existing URL, request, response, WebSocket, and save contracts.
- Keep FastAPI as the sole production service and static-file host.
- Do not touch the live `8000` service, tunnel, or live game save.
- Develop only in the existing isolated Vue migration worktree.
- Keep legacy fallback until Vue coverage and regression verification are complete.

## Review Focus

- An unclaimed, assigned seat remains operable without a player account.
- Traveler role selection uses the complete role pool and preserves alignment on later changes.
- A storyteller can inspect closed chat archives but cannot send to a closed chat.
- End-game undo returns to the live grimoire without discarding review data.
- All irreversible-looking actions use explicit in-UI confirmation and remain disabled offline.

---

### Task 1: Traveler administration

**Files:** Create `frontend/src/components/storyteller/TravelerPanel.vue`; modify `frontend/src/services/storyteller.js`, `frontend/src/components/storyteller/GameControlPanel.vue`, `frontend/src/components/storyteller/StorytellerLiveView.vue`, `frontend/src/styles/storyteller.css`; test `frontend/tests/storyteller-traveler.test.js`.

**Interfaces:** Consumes `view.travelers`, `view.traveler_roles`, `view.traveler_recommended`, `view.current`. Produces `addTraveler(name)`, `assignTraveler(id,role,align)`, `setTravelerExile(id,exiled)`, `toggleTravelerAlive(id)` on storyteller service; emits corresponding events from `TravelerPanel`.

- [ ] Write component tests first: add trimmed name; select good/evil and recommended/other roles; toggle life; require two-click exile but one-click unexile; disable writes offline; ignore blank name.
- [ ] Run `cd frontend && npm test -- storyteller-traveler.test.js`; expect failures from missing component/behavior.
- [ ] Implement the component and service calls using `/api/traveler/add`, `/assign`, `/exile`, `/alive`; wire to `StorytellerLiveView.run` and render in controls without displacing day/night panels.
- [ ] Run the targeted tests, then `cd frontend && npm test`; expect all pass.
- [ ] Commit the tested task.

### Task 2: Storyteller chat supervision

**Files:** Create `frontend/src/components/storyteller/StorytellerChatPanel.vue`; modify storyteller service, `StorytellerLiveView.vue`, control/context panel and CSS; test `frontend/tests/storyteller-chat-admin.test.js`.

**Interfaces:** Consumes `view.chats`; produces service methods `answerChatInvite(id,accept)`, `sendStorytellerChat(id,text)`, `leaveStorytellerChat(id)`, `closeStorytellerChat(id)`, `recallChats()`; emits those intents from panel.

- [ ] Write tests first for active/archive rendering, invite accept/reject, own-member send, unauthorized send hidden, close/recall confirmation, and offline disable.
- [ ] Run targeted test; expect missing component/behavior failure.
- [ ] Implement focused panel and service methods with `/api/chat-st/{id}/*` and `/api/chat-st/recall`; route events through page command wrapper.
- [ ] Run targeted and full frontend tests; expect all pass.
- [ ] Commit the tested task.

### Task 3: Seat administration and room/session controls

**Files:** Modify `frontend/src/components/storyteller/PlayerDetailPanel.vue`, `ContextPanel.vue`, `StorytellerLiveView.vue`, `StorytellerHeader.vue`, `frontend/src/services/storyteller.js`, CSS; create `frontend/src/components/storyteller/SessionPanel.vue`; tests `frontend/tests/storyteller-seat-admin.test.js`, `frontend/tests/storyteller-session-admin.test.js`.

**Interfaces:** Service methods `setRoom(code)`, `setFake(payload)`, `setMarker(payload)`, `setRedHerring(seat)`, `toggleSeatAlive(seat)`, `togglePlayerAlive(playerId)`, `removePlayer(playerId)`, `loadSave()`, `resetGame()`.

- [ ] Write failing tests for player/empty-seat alive toggle, markers with role/team/mad payloads, fake identity, red herring, remove confirmation, four-digit room validation, load/reset two-click confirmation, offline disable.
- [ ] Run targeted tests; expect failures from absent controls/service calls.
- [ ] Implement focused seat and session controls using existing endpoints; keep transient picker state local to the component.
- [ ] Run targeted and full frontend tests; expect all pass.
- [ ] Commit the tested task.

### Task 4: End-game and review

**Files:** Create `frontend/src/components/storyteller/EndGamePanel.vue`, `frontend/src/components/storyteller/ReviewPanel.vue`; modify `StorytellerLiveView.vue`, `GameControlPanel.vue`, `ContextPanel.vue`, storyteller service and CSS; test `frontend/tests/storyteller-review-admin.test.js`.

**Interfaces:** Consumes `view.winner`, `view.review.groups[].items[].mark`; produces service methods `setWinner(winner)`, `markReview(seat,night,wrong)`; local `reviewOpen` is presentation-only.

- [ ] Write failing tests for winner choice and undo, review timeline rendering, mark/unmark, no-data state, and return to grimoire without changing server state.
- [ ] Run targeted test; expect missing functionality failure.
- [ ] Implement panels and command wiring using `/api/end` and `/api/review/mark`.
- [ ] Run targeted and full frontend tests; expect all pass.
- [ ] Commit the tested task.

### Task 5: Frontend acceptance and legacy fallback removal readiness

**Files:** Modify `docs/migration/vue-vite-status.md`, `README.md`; test `frontend/tests/storyteller-admin-coverage.test.js`.

**Interfaces:** Consumes completed Task 1–4 controls; produces a Vue storyteller page with no operational links to `/legacy/`.

- [ ] Write a failing integration test that mounts storyteller in lobby, day, night, and ended states and proves all administration entrances are native; test service payloads against real request builder.
- [ ] Run targeted test; expect legacy-link or missing-entry failure.
- [ ] Remove legacy links/fallbacks after coverage is demonstrated and update migration documentation.
- [ ] Run `npm test` and `npm run build`; run backend unittest suite and isolated smoke test; expect all pass.
- [ ] Commit the tested task.
