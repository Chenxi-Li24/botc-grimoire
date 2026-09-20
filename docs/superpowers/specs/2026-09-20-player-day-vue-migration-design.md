# Player and Storyteller Day Vue Migration Design

## Intent

Complete the next two production migration slices without reproducing the legacy monolith:

1. keep joined and returning players inside the Vue application for their complete game-facing experience;
2. let the storyteller run the complete daytime nomination and execution loop from the Vue grimoire.

The existing FastAPI game rules, WebSocket projections, local-storage identity, and save-file format remain authoritative. The work is a UI migration with only narrowly scoped backend projection or validation changes when the existing contract cannot express an already-supported behavior.

## Confirmed Scope

### Player application

The Vue player application must cover every state currently reached through `renderPlayer`:

- lobby identity, public setup information, wishes, seat claiming and seat changes;
- optional self-entry as a traveler where the existing server permits it;
- private perceived role card, alignment changes, role changes, demon bluffs and Lunatic information;
- public seat circle, alive/dead state, public deaths, fabled characters and nominations;
- night wake prompts, target/character selection, Demon and Lunatic kill choices, storyteller replies, grimoire reveal and madness notice;
- daytime nomination selection, voting, dead-vote confirmation and nomination history;
- player-managed private chat, invitations, requests, messages, leaving and closing;
- final result, revealed roles and the read-only review timeline.

Joining successfully and restoring a valid `player_id` must render this Vue page directly. It must no longer redirect to `/legacy/`.

### Storyteller daytime application

The existing Vue storyteller shell must gain:

- talk and nomination stage switching;
- storyteller-created nominations for seats or travelers;
- a live vote board with both player-submitted and storyteller-recorded votes;
- pass/fail resolution, execution state and nomination history;
- ending the day and entering the next night;
- visibility of public deaths and the currently pending execution.

The grimoire remains central and selected seats remain usable while the daytime control panel is open.

## Explicit Non-Goals

This slice does not migrate:

- storyteller traveler creation, assignment, alignment, exile or life controls;
- storyteller chat supervision and recall;
- storyteller winner declaration, end-game undo, or editable review annotations;
- generic storyteller room-code, reset, load-save, seat administration or arbitrary marker controls;
- JSON/PDF script importing;
- general backend router/domain decomposition outside changes required by this slice.

Those functions remain reachable through the legacy escape until their own migration slices are complete.

## Approach

Use the existing REST endpoints and WebSocket views as the compatibility boundary. Do not copy the legacy HTML renderer into Vue and do not couple this slice to a broad backend rewrite.

The server stays authoritative. Components own only temporary interaction state such as a selected nominee, selected night targets, an unsent chat message or the active result tab. Every accepted command is reflected through the next WebSocket projection.

## Frontend Structure

### Player feature

Create focused modules under `frontend/src/components/player/`:

- `PlayerShell.vue`: mobile-first page regions and connection state;
- `PlayerLobby.vue`: wishes, seats and traveler self-entry;
- `PlayerRoleCard.vue`: private identity and information;
- `PlayerBoard.vue`: public seat circle and selection surface;
- `PlayerNightAction.vue`: kill, player-target and character-target prompts;
- `PlayerDayAction.vue`: nomination and vote controls;
- `PlayerChat.vue`: player-side chat workflow;
- `PlayerResult.vue`: settlement and review views.

`frontend/src/pages/PlayerPage.vue` composes the feature. `usePlayerView` owns the authenticated player WebSocket lifecycle. `usePlayerActions` owns ephemeral selections and invokes a dedicated player service. Pure presentation helpers format teams, phases, deaths, nominations and review records without embedding network calls in components.

### Storyteller day feature

Create focused modules under `frontend/src/components/storyteller/day/`:

- `DayControlPanel.vue`: phase summary and stage switching;
- `NominationComposer.vue`: nominator and nominee selection;
- `VoteBoard.vue`: threshold, voters and storyteller vote toggles;
- `NominationHistory.vue`: current-day and prior-day results;
- `DayResolution.vue`: pass/fail resolution and end-day confirmation.

The existing `StorytellerLiveView` selects the day control panel when the phase is `day`. Day commands are added to the existing storyteller service and command wrapper, preserving connection disabling and normalized errors.

## Routing and Session Behavior

- No `player_id`: render the Vue join page.
- Valid `player_id`: render `PlayerPage` at the root hash route.
- Invalid or expired `player_id`: clear it and return to the join page.
- `#/storyteller`: continue to render the Vue storyteller page.
- `#/storyteller-preview`: continue redirecting to `#/storyteller`.

The legacy application remains mounted during this slice only as a fallback for the explicit non-goals. Player routing must not use it during normal play.

## Shared Presentation Model

Player and storyteller day components share pure helpers for:

- participant identity across numbered seats and traveler IDs;
- nomination labels, voter chips, vote threshold and execution state;
- phase/day labels and public death groups;
- role/team labels that are safe for the current audience.

Private role information must only come from the current player's server projection. Shared helpers must never derive or expose another seat's secret role from storyteller-shaped data.

## Error and Reconnection Behavior

- A disconnected WebSocket disables state-changing controls but leaves the last projection visible.
- REST validation errors appear beside the affected interaction and do not discard the user's local selection or chat draft.
- A player removed or invalidated by the storyteller is returned to the join page and their stored ID is cleared.
- Duplicate submissions are prevented by per-command pending keys.
- Destructive or irreversible interactions use the existing two-step in-page confirmation pattern, including dead votes, nomination resolution and ending the day.

## Backend Contract Policy

Existing endpoints remain stable. The implementation may add fields to player or storyteller projections when required for an already-supported legacy behavior, but it must not expose storyteller-only information to players. New command endpoints are allowed only if an existing endpoint cannot safely express a command; they must follow the current authentication and error conventions.

The existing seat-centric state, night workflow and save schema remain unchanged.

## Testing

Development follows test-driven slices:

- routing tests prove new and returning players stay in Vue and invalid sessions return to join;
- service tests cover each player and storyteller day endpoint with normalized errors;
- component tests cover lobby/seat behavior, role privacy, night choices, nominations, dead votes, chats, settlement and review;
- storyteller tests cover stage switching, nomination composition, live votes, resolution and ending the day;
- audience-boundary tests prove player components receive no other player's private identity;
- the complete frontend suite, production build, backend unit suite, Python compilation and backend smoke test run before cutover;
- browser acceptance covers a phone viewport for every player phase and desktop/tablet viewports for the storyteller day workflow.

## Cutover and Rollback

The player route switches only after all player states are implemented and the complete regression suite passes. The storyteller day link to legacy remains until its full workflow passes the same gate. `frontend/legacy/` is not deleted in this slice, so rollback consists of restoring the prior route selection without changing save data.

## Acceptance Criteria

- A player can join, claim a seat, play through night and day, chat, reconnect and view the result without loading `/legacy/`.
- A storyteller can conduct the daytime talk/nomination/vote/execution/end-day loop without loading `/legacy/`.
- Both views remain synchronized through the existing WebSocket server.
- Mobile player controls and desktop storyteller controls remain stable as content changes.
- Existing saves load unchanged and no player projection leaks another player's private role information.
