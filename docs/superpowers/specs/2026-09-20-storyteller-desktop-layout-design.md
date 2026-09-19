# Storyteller Desktop Layout Design

## Context

The storyteller interface is used primarily on a computer. The legacy page places lobby configuration, destructive actions, fabled roles, the grimoire, and joining information in one long visual stream. These controls have similar visual weight, the grimoire is not the dominant object, and important information moves below the fold as more panels appear.

This design migrates the storyteller interface to Vue while reorganizing it around the storyteller's live workflow. It is a focused extension of `2026-09-20-vue-vite-modular-migration-design.md`; it does not change game rules or server contracts.

## Goals

- Optimize the storyteller interface for a computer, with `1366x768` as the minimum primary viewport.
- Keep the grimoire, phase, selected player, and current primary action visible without scrolling the document.
- Give high-frequency and time-sensitive actions stronger priority than setup and maintenance controls.
- Replace the legacy page's single large rendering flow with independently testable Vue components.
- Preserve every existing storyteller function, REST/WebSocket contract, local-storage key, and JSON save format.
- Keep `/legacy/#/storyteller` available until the Vue storyteller slices have passed regression testing.

## Non-goals

- Redesigning the player-facing mobile interface.
- Adding multi-room support, accounts, a database, or new game rules.
- Reworking backend domain logic during this frontend migration.
- Optimizing the storyteller interface for phone-sized screens. Narrow windows receive a usable fallback, not a separate phone workflow.

## Desktop Shell

The page uses a fixed-height application shell rather than a scrolling document.

```text
+------------------------------------------------------------------+
| Grimoire | room | script | phase                    primary | ... | 64 px
+--------------+--------------------------------+------------------+
| Game control |                                | Current context  |
| 260 px       |          Grimoire              | 320 px           |
|              |          flexible              |                  |
| setup/phase  |       seats stay visible       | join/player/     |
| night steps  |                                | night/vote       |
| advanced     |                                |                  |
+--------------+--------------------------------+------------------+
```

The content grid is `260px minmax(560px, 1fr) 320px`, with 16 px gaps and outer padding. The shell height is `100dvh`; the header consumes 64 px and the three content columns fill the remainder. The document body does not scroll. The left and right panels may scroll independently, while the central grimoire stays fixed.

At widths below 1180 px, the side panels become overlay drawers opened from the header. This is a narrow-window fallback only; the primary acceptance target remains 1366 px and wider.

## Header

The fixed header contains only global state and the action most relevant to the current phase:

- product title;
- room code;
- script name;
- lobby/day/night and stage indicator;
- connection status;
- one primary action;
- a `More` menu.

The primary action changes with server state:

- lobby: assign roles or start, according to the existing readiness rules;
- night: complete the current step or advance;
- day discussion: enter nomination;
- nomination/voting: perform the next valid phase transition.

Load and reset live in the `More` menu. Reset remains visually dangerous and retains a two-step confirmation. Phase-invalid actions are not displayed as primary actions.

## Left Panel: Game Control

During the lobby, the left panel contains:

- script selection;
- player count;
- manual/random role assignment entry points;
- start readiness and start action;
- a collapsed `Advanced settings` section.

Advanced settings contain fabled roles, Sentinel outsider adjustment, and other low-frequency setup controls. Fabled choices use a searchable or grouped compact list rather than occupying the page's main horizontal flow.

After the game starts, script and player count become a read-only summary. The panel's main content changes to phase controls and the ordered night/day workflow. Completed steps are visually subdued, the current step is prominent, and future steps remain visible for orientation.

## Center Panel: Grimoire

The grimoire is the visual and interaction center of the page.

- Its board scales within the available center column, targeting a 560-650 px diameter at the minimum desktop viewport.
- Seat number, player name, life state, and relevant public/private storyteller markers are visible on the seat node.
- Empty seats are visually quiet.
- The selected seat has one unambiguous highlight.
- The player involved in the current night step, nomination, or vote receives a separate contextual highlight.
- Clicking a seat changes local selection and opens the corresponding detail in the right panel; it does not directly mutate game state.
- Player-specific action controls no longer appear below the board.

The center panel may show small status overlays, but it must not become another vertically scrolling control list.

## Right Panel: Current Context

The right panel answers one question: what does the storyteller need to inspect or do now?

Its priority order is:

1. an explicit seat/player selection;
2. the current blocking phase operation;
3. the default panel for the current game state.

Default lobby content is the join QR code, room code, joined players, and seating progress. Selecting a seat replaces this with player details and valid player operations. At night, the current role instructions, targets, reply controls, and completion action are shown. During nominations and voting, it shows nominees, vote progress, voters, and close/resolve actions.

Only the right panel scrolls when this content exceeds the viewport. Closing a selection returns to the phase-default context.

## Component Boundaries

```text
StorytellerPage
|- StorytellerHeader
|- GameControlPanel
|  |- SetupControls
|  |- PhaseControls
|  |- NightStepList
|  `- AdvancedSettings
|- GrimoireBoard
|  `- SeatNode
`- ContextPanel
   |- JoinPanel
   |- PlayerDetailPanel
   |- NightActionPanel
   |- NominationPanel
   `- VotePanel
```

`StorytellerPage` owns the latest server view, connection state, selected seat, and active context. Child components receive data through props and emit intent events. They do not create WebSocket connections or keep duplicate copies of server-owned game state.

Shared behavior is separated into:

- `services/storyteller.js` for authenticated REST commands;
- `services/websocket.js` for reconnecting socket transport;
- `composables/useStorytellerView.js` for the current server projection and connection state;
- `composables/useConfirmAction.js` for two-step dangerous actions.

REST command responses are acknowledgements only. The following WebSocket projection remains the authoritative rendered state.

## Interaction and Error Handling

- A disconnected socket leaves the latest view visible, marks the connection as reconnecting, and disables state-changing actions.
- Authentication failure returns to the storyteller password entry without clearing unrelated player storage.
- REST errors appear inside the panel that initiated the command and do not collapse the whole shell.
- While a command is pending, only the initiating action is disabled.
- Server updates that remove the selected player clear the selection and restore the phase-default context.
- Every destructive operation keeps the existing two-step confirmation behavior.

## Visual Hierarchy

- The grimoire receives the largest area and highest contrast boundary.
- The header phase badge and primary action are the next strongest elements.
- Side panels use quieter surfaces and compact controls.
- Destructive actions use danger styling only at the point of action, not as a permanent competing button in the header.
- Status markers use both icon/text and color so meaning is not color-dependent.
- Focus outlines and keyboard navigation remain visible for all controls.

## Migration Strategy

The storyteller migration is delivered in reversible slices:

1. Add the Vue storyteller route, authenticated WebSocket view service, and desktop shell.
2. Migrate the grimoire board and lobby join context without state-changing player operations.
3. Migrate setup, role assignment, advanced settings, and start controls.
4. Migrate selected-player operations, phase controls, and the night workflow.
5. Migrate nominations, voting, travelers, chats, ending, and review panels.
6. Run full regression and desktop visual acceptance, then remove the storyteller dependency on the legacy route.

Until a slice is complete, its entry point continues to send the storyteller to `/legacy/#/storyteller`. A partial Vue panel must not silently omit an existing storyteller capability.

## Testing and Acceptance

Automated coverage includes:

- header primary action selection for lobby, night, day, nomination, and voting states;
- context-panel priority and selection clearing;
- WebSocket reconnect/authentication behavior;
- grimoire seat selection and emitted intents;
- dangerous-action confirmation;
- component tests for setup, night, nomination, and vote controls;
- existing Python smoke tests to verify unchanged API and privacy contracts.

Manual acceptance at `1366x768` and a larger desktop viewport requires:

- no document-level vertical or horizontal scrolling;
- the complete grimoire, phase indicator, primary action, and right-panel heading visible at once;
- lobby QR code and room code visible without scrolling the document;
- left and right panels independently scroll when necessary;
- reset cannot be triggered with one click;
- all legacy storyteller workflows remain reachable during migration;
- no browser console errors during lobby, night, day, nomination, and review checks.

## Success Criteria

The storyteller can run the game from one stable desktop workspace: the board never disappears while controls are used, the current task is always identifiable, low-frequency setup no longer competes with live-game actions, and future changes can be made within focused Vue components rather than a single large renderer.
