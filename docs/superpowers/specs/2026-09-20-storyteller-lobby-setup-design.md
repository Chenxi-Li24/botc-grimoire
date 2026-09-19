# Storyteller Lobby Setup Migration Design

## Context

The Vue storyteller preview currently provides the desktop shell, live read-only grimoire, lobby joining context, and selected-player inspection. All state-changing storyteller work still requires the legacy console.

This slice migrates the complete pre-game setup workflow into the Vue preview. It extends `2026-09-20-storyteller-desktop-layout-design.md` without changing backend rules, REST/WebSocket contracts, local-storage keys, or save compatibility. The production storyteller route remains on the legacy console until every storyteller workflow has migrated.

## Goals

- Let the storyteller configure and start a lobby without leaving the Vue preview.
- Keep the grimoire visible while selecting roles and reviewing assignment state.
- Split setup behavior into focused Vue components instead of recreating the legacy monolith.
- Preserve random assignment, complete manual assignment, fabled roles, Sentinel adjustment, and forced start behavior.
- Treat the WebSocket projection as the authoritative rendered game state.

## Non-goals

- Migrating save, load, reset, room-code rotation, or other maintenance actions.
- Migrating night, day, nomination, voting, traveler, chat, ending, or review controls.
- Changing player-facing pages, backend behavior, game rules, or persistence formats.
- Switching `/#/storyteller` away from `/legacy/#/storyteller`.
- Persisting an unsubmitted manual-assignment draft across refreshes.

## Route and Compatibility Boundary

- `/#/storyteller-preview` hosts the Vue migration preview and gains lobby setup controls.
- `/#/storyteller` continues to redirect to `/legacy/#/storyteller`.
- The visible `打开完整控制台` escape remains available for every workflow not migrated in this slice.
- When the server view changes from `lobby` to `playing`, setup controls become a read-only summary. The preview does not expose partial live-game mutations.

## Architecture

`StorytellerLiveView` remains the sole owner of the latest WebSocket projection, connection state, selected seat, and top-level panel context. Lobby components receive the current projection through props and emit explicit intent events. They never establish their own WebSocket connection and never keep a second copy of server-owned state.

State-changing requests pass through two shared modules:

- `services/storyteller.js` sends authenticated storyteller REST commands, parses backend errors, and exposes one function per existing lobby endpoint.
- `composables/useStorytellerCommand.js` owns pending and local error state for an initiating operation and prevents writes while the socket is disconnected.

REST responses are acknowledgements only. Components do not merge them into the current view. After a successful command, the next WebSocket projection updates the interface.

The only substantial local domain state is the manual-assignment draft. It belongs to the manual-assignment feature and is cleared when the storyteller cancels, confirms successfully, changes the server configuration, or the game leaves the lobby.

## Component Boundaries

```text
StorytellerLiveView
|- StorytellerHeader
|- GameControlPanel
|  `- LobbySetupPanel
|     |- SetupControls
|     |- RoleAssignmentControls
|     |- AdvancedSettings
|     `- StartControl
|- GrimoireBoard
|  `- SeatNode
`- ContextPanel
   |- JoinPanel
   |- PlayerDetailPanel
   `- ManualAssignmentPanel
      |- RolePicker
      |- SpecialRoleFields
      `- BluffPicker
```

Responsibilities:

- `LobbySetupPanel` selects the appropriate setup subsection and becomes read-only after the game begins.
- `SetupControls` edits the script and player count and owns the two-step destructive configuration confirmation.
- `RoleAssignmentControls` enters manual mode or arms the two-step random-assignment confirmation.
- `AdvancedSettings` contains collapsed fabled-role and Sentinel controls.
- `StartControl` appears only when the backend projection reports that a partially seated, fully assigned lobby can start.
- `ManualAssignmentPanel` coordinates the local draft for the selected seat and global bluff choices.
- `RolePicker` groups roles by townsfolk, outsider, minion, and demon.
- `SpecialRoleFields` edits role-specific manual-assignment metadata already supported by the legacy request contract, including drunk false roles and lunatic information.
- `BluffPicker` selects the three demon bluffs allowed by the current script.

## Lobby Setup Interaction

The left panel begins with script and player-count controls. Changing either value is destructive because the existing backend clears seats and role assignments. The first activation arms an inline warning that states the impact; a second activation within the confirmation window submits `/api/config`. Changing the proposed values or allowing the confirmation to expire disarms it.

Advanced settings stay collapsed by default so fabled roles and Sentinel adjustment do not compete with common setup actions. Each setting submits independently through the existing `/api/fabled` or `/api/sentinel` endpoint. Server-side validation messages remain inside this section.

Random assignment is explicitly described as `发牌并进入第一夜`. The first activation displays the current script, player count, and computed team composition. The second confirmation submits `/api/assign`. This is a UI safety layer only; backend behavior remains unchanged.

When every seat has a preassigned role but not every player has joined, `StartControl` exposes the existing forced-start behavior through `/api/start`. The control explains that late players inherit the preassigned role of the empty seat they take.

## Manual Assignment Interaction

Entering manual mode copies the current `seat_roles`, bluffs, and supported special-role metadata into a local draft. No request is made at entry.

The grimoire stays centered and visible. Clicking a seat selects it; the right panel replaces its normal context with `ManualAssignmentPanel`. The role picker shows roles grouped by team. Choosing a role updates only the draft and immediately previews the role on that seat. Choosing the same role again clears it.

The draft reports:

- assigned seats versus required seats;
- actual versus expected team composition, including existing script adjustments and Sentinel changes; composition differences are warnings, while the existing hard rules of exactly one demon and at least one minion block submission;
- duplicate-role conflicts;
- missing or invalid special-role metadata;
- demon bluff progress and conflicts with roles already in play.

Role-specific fields appear only for the selected role. The migration preserves every field accepted by the existing `/api/assign/manual` payload, including false-role and lunatic-related metadata. Global demon bluffs remain at the bottom of the manual panel and use the same script-specific role restrictions as the legacy console.

`确认发身份` stays disabled until every seat is assigned and the existing hard-role, duplicate, bluff, and special-role validations pass. A nonstandard townsfolk/outsider distribution remains a visible warning and does not introduce a new client-side prohibition. Confirmation submits the existing `{ assignments, bluffs, fakes }` body. A successful acknowledgement exits manual mode and waits for the WebSocket projection. Cancel discards the entire local draft without contacting the backend.

Changing the server configuration, receiving a non-lobby view, or losing the selected seat invalidates the draft and exits manual mode. Refreshing the page also discards the draft by design.

## Connection, Pending, and Error Behavior

- `connected` permits lobby mutations; `connecting` and `reconnecting` leave the latest view visible but disable every write.
- Only the initiating control is pending during an ordinary request. Other panels remain readable.
- Backend error messages appear inside the component that initiated the command and do not collapse the shell.
- Authentication failure continues to clear only the storyteller password and returns to the password entry.
- A successful REST acknowledgement does not optimistically rewrite the view.
- Commands that require a visible server transition remain pending until a matching WebSocket projection arrives or a bounded timeout reports that synchronization is delayed.
- Destructive confirmation state is local, short-lived, and cleared when its underlying inputs change.

## Accessibility and Desktop Layout

- The existing `1366x768` minimum desktop target and three-column shell remain unchanged.
- Manual mode does not introduce document scrolling; the right panel scrolls independently when the role list exceeds the viewport.
- All buttons expose visible keyboard focus.
- Team, validation, selected-seat, and pending states use text or icons in addition to color.
- Disabled controls explain whether the cause is disconnection, invalid draft state, or an incompatible game phase.

## Verification Strategy

At the user's direction, implementation proceeds through the complete lobby slice before tests are added or run. Verification is consolidated after the migration code is complete rather than performed per component.

The final verification phase adds and runs automated coverage for:

- authenticated storyteller request construction and backend error parsing;
- disconnected and reconnecting write prevention;
- destructive configuration confirmation;
- two-step random assignment;
- manual draft selection, cancellation, invalidation, duplicates, composition warnings, hard demon/minion rules, and special-role fields;
- three demon bluffs and script-specific eligibility;
- fabled and Sentinel mutations;
- forced-start visibility and behavior;
- transition from editable lobby controls to a read-only playing summary;
- preservation of the formal legacy storyteller route.

After the consolidated frontend suite passes, verification includes the production Vite build, backend unit tests, Python compilation, the existing backend smoke test, and browser acceptance at `1366x768` and `1600x900`. Browser acceptance checks configuration, manual and random assignment, advanced settings, forced start, error presentation, reconnect disabling, absence of document overflow, and the legacy-console escape.

## Success Criteria

- A storyteller can configure a script and player count, set fabled and Sentinel options, assign roles randomly or manually, and start a prepared partial lobby from the Vue preview.
- The grimoire stays visible throughout assignment and accurately previews the local manual draft.
- Accidental configuration resets and accidental random starts require two explicit actions.
- Every server mutation uses the existing API contract and the following WebSocket projection remains authoritative.
- Entering live play removes editable lobby controls and leaves all unmigrated operations reachable in the legacy console.
- The complete consolidated test and acceptance pass succeeds before this slice is considered complete.
