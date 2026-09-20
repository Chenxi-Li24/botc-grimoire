# Storyteller Night Engine and Workflow Design

## Intent

Replace the legacy storyteller night panel with a Vue 3 + Vite workflow backed by a correct, seat-centric night engine. The product must help the storyteller run first and later nights in order, preserve storyteller discretion, automate deterministic information, retain the provenance of every effect and message, and support offline table play where no player account has claimed a seat.

The migration must not copy the legacy monolithic renderer or its player-bound state model. It establishes reusable boundaries for later day-flow and script-pack work.

## Confirmed Product Rules

- Night order has distinct first-night and other-night sheets.
- Only character instances currently in play appear in the night order; an unclaimed seat with an assigned character is still in play.
- A player account claims a seat and receives its private state. The seat, not the account, owns character, alignment, life, effects, actions, and history.
- Going backward or jumping in the night sheet never reverses state.
- Every executed step exposes an explicit undo action that previews and reverses its dependent events.
- Lunatic acts before the real Demon. The real Demon is shown the Lunatic and the Lunatic's chosen target before making its own decision.
- A player secretly killed before their normal step is not woken for an ordinary ability, but death-triggered abilities still resolve.
- Night deaths remain private until dawn.
- Incomplete required work produces a warning, but the storyteller can explicitly force the workflow forward.
- The previous/next controls never move when instruction length changes.

## Scope

This slice includes:

- the canonical seat-owned game state required by the night engine;
- a per-seat, dynamically generated first/other-night action queue;
- navigation, forced continuation warnings, and event-scoped undo;
- player and storyteller-proxy night choices;
- confidential death adjudication and death-trigger scheduling;
- structured information calculation, delivery, correctness, and review history;
- sourced, timed, suspendable status effects;
- cognitive overlays such as Drunk and Lunatic;
- Pit-Hag character creation and dynamic night-order changes;
- required persistent character state for supported script characters;
- official Simplified Chinese labels and reminders for the three official editions;
- a normalized runtime script/character contract that future JSON/PDF importers can target.

This slice does not implement PDF OCR/import UI, general chat, traveler administration, day nominations/voting, save-browser UI, or end-game presentation. It may migrate save data to the new seat model and must keep legacy saves readable.

## Existing Problems

The existing implementation duplicates character and life state between `Player` and `seat_roles`, applies Demon kills only at dawn, keys most night steps by character rather than acting seat, moves Lunatic steps inconsistently, applies Pit-Hag changes immediately, stores status as unsourced marker strings, and treats poisoned/Drunk information as automatically false. Night interactions are largely hard-coded to one community script.

These are engine defects, not presentation defects. The Vue workflow must consume corrected contracts rather than reproduce the old assumptions.

## Architecture

```text
Character catalog + script manifest + zh-CN locale
                         |
                         v
                  runtime pack compiler
                         |
                         v
Seat state + effect ledger + event journal
                         |
                         v
               dynamic night queue engine
                   /             \
                  v               v
       information resolver    outcome adjudicator
                  \               /
                   v             v
                storyteller WebSocket view
                         |
                         v
          Vue night navigation and task panels
```

The server is authoritative. The client holds only an unfinished selection draft, expanded/collapsed UI state, and the currently inspected step or seat.

## Canonical Seat Model

Each configured seat exists independently of an online player:

```text
SeatState
  seat: integer
  claimed_by: player id | null
  character_id: stable character id | null
  perceived_character_id: stable character id | null
  alignment: good | evil
  alive: boolean
  died_at: event reference | null
  effects: active effect ids
  ability_state: character-keyed structured state
```

Player accounts own only identity, connection, preference/wish, and their current seat claim. Claiming a seat reveals the seat's private identity; leaving or disconnecting does not erase or move the seat's game state. The storyteller can operate every assigned seat whether claimed or not.

Legacy saves are migrated by folding `Player.role_id`, player life state, `seat_roles`, `seat_alive`, fake identities, and marker maps into canonical seats. Save output uses the new representation after a successful load.

## Character and Script Runtime Contract

Stable English character IDs remain persistence keys. Presentation text is supplied by locale data. The three official editions use the official Simplified Chinese script names, character names, ability text, and night reminders. Community scripts retain source-specific display overrides without mutating the shared official catalog.

Character definitions declare capabilities rather than embedding UI logic:

- action timing: start-knowing, first night, each night, each night except first, passive, death-trigger, retrospective;
- ordered night position for first and other nights;
- selection schema: players, characters, counts, eligibility;
- information schema and resolver key;
- effects created and their lifetime policy;
- death/outcome semantics;
- optional complex handler key.

Common capabilities use reusable handlers. Pit-Hag, Fang Gu, Lil' Monsta, and other non-composable abilities use named complex handlers. An unknown imported custom character may run in manual-only mode with visible instructions; the engine must never pretend it has automated an unknown rule.

## Dynamic Night Queue

The queue is a list of action instances, not character names:

```text
NightStep
  id: stable event-local id
  actor_seat: integer | null
  character_id: stable character id | special step
  perceived_as: stable character id | null
  trigger: normal | death | created | start-knowing | traveler | special
  status: upcoming | current | completed | skipped | undone
  skip_reason: string | null
```

Generation rules:

1. Select the first-night or other-night sheet.
2. Add special dusk, meeting, and dawn steps only when their conditions apply.
3. Add one action instance per in-play seat character or perceived character ability.
4. Do not require a claimed player.
5. Retain conditional in-play characters as visible steps, but mark them automatically skipped with a reason when their trigger did not occur.
6. Recalculate only the unexecuted suffix when character, life, alignment, or ability state changes.

Drunk acts in the standard position of the character they believe they are. Drunk/poisoned actors are woken and make choices normally; the effect changes whether their ability works and what information may be delivered, not whether they appear to act.

## Lunatic and Demon Flow

Lunatic action precedes real Demon action:

1. Lunatic is woken as their perceived Demon and chooses a target.
2. The choice is recorded as performance-only and causes no death.
3. At the real Demon step, the interface identifies the Lunatic and shows that target.
4. The real Demon then submits its own choice.
5. The storyteller adjudicates the real outcome without revealing it to players until dawn.

The information remains available to the real Demon even when the Demon uses a different target.

## Outcome and Confidential Death Adjudication

A selection is not a death. Each killing action creates a pending outcome. The storyteller can resolve it as:

- confirmed secret death;
- no death;
- delayed death;
- substituted or redirected death;
- character/alignment transformation;
- recorded choice with no death effect.

The adjudicator displays active protections, source incapacity, already-dead targets, replacement rules, and character-specific consequences. The storyteller remains the final authority.

A confirmed secret death updates the storyteller view and future action eligibility immediately while public/player views continue to show the player alive until dawn. Ordinary future abilities are skipped; Ravenkeeper-style night-death triggers are inserted; Sage-style triggers require the recorded source to be a Demon attack.

Every death records source seat, source character, ability/event, phase/step, whether it was a Demon attack, whether it was arbitrary, and any prevented/replaced outcome. This provenance drives triggers and review.

## Pit-Hag Flow

Pit-Hag submission creates a pending transformation card rather than immediately mutating the game. The card shows target character and alignment, proposed character, in-play conflict, relative night position, affected future steps, and Demon-creation consequences.

On confirmation:

- an already-in-play character, including a dead character, produces a silent failure visible only to the storyteller;
- the target receives the new character while retaining their current alignment;
- the old character ability and persistent effects are removed or suspended as rules require;
- a new passive ability starts immediately;
- a start-knowing ability creates an immediate information step even outside the first night;
- a normal action whose standard position is after Pit-Hag is inserted at that standard position;
- a normal action whose position has passed waits until the next night;
- the old character's unexecuted step is removed.

If a Demon is created, all deaths that night become storyteller-arbitrary. The created Demon does not perform its ordinary choose-a-player-to-die action that night. Non-kill parts of its ability start immediately: for example Vortox information constraints and No Dashii poisoning. Kill-dependent Fang Gu, Vigormortis, and Imp consequences do not trigger without a qualifying Demon kill. Arbitrary deaths are attributed to Pit-Hag, so they do not falsely trigger abilities that require being killed by a Demon.

Undo reverses the transformation transaction and previews dependent steps, effects, messages, and outcomes that will also be reversed.

## Structured Information System

Information delivery is a pipeline:

```text
game facts
  -> legal truth/candidate set
  -> registration choices
  -> impairment and false-information constraints
  -> delivery policy
  -> sent payload + truth annotations + effect snapshot
```

Information with exactly one legal result and no active ambiguity is sent automatically. The storyteller receives a visible non-blocking notice containing the recipient and exact payload. Examples include an unimpeded numeric result after all registration decisions are already fixed.

Information pauses for storyteller adjudication when any of these apply:

- Drunk, poisoned, Vortox, Brewer-style override, or another information modifier;
- Spy/Recluse or other registration discretion;
- the ability requires choosing valid candidates or decoys;
- the result contains multiple semantic claims;
- the engine lacks a trusted resolver.

Each delivery records actor seat, real and perceived character, targets, true result, delivered result, per-claim truth, registration decisions, active-effect snapshot, reason for false/forced-false information, send/delivery timestamps, and source event.

Dreamer stores target, one displayed good character, one displayed evil character, and truth independently for both displayed items. This supports a normal one-true answer as well as poisoned/Vortox-invalid combinations and makes review unambiguous.

Drunk follows the action and information schema of their perceived character. Their information may be true or false; it is never automatically classified false. A storyteller-composed impaired response requires an explicit correct/incorrect annotation at send time, with review-time correction available.

## Sourced Effect Ledger

Status is modeled as effects and transitions rather than marker strings:

```text
Effect
  id, type, target_seat
  source_seat, source_character, source_event
  payload
  started_at
  lifetime_policy
  expected_end
  state: active | suspended | ended
  transitions[]: time, from, to, reason
```

Lifetime policies are semantic game triggers rather than wall-clock seconds: until dusk, until next choice, while source has ability, fixed number of days/nights, game-long, or manual.

- Poisoner poison lasts through the night and following day and ends at dusk. It suspends while its source temporarily lacks the ability and ends early only on permanent source-character loss or another rule-defined terminal event.
- Widow poison remains while Widow has the ability; it ends on death or permanent character loss, suspends while Widow is drunk/poisoned, and resumes if the ability returns.
- Cerenovus madness records the claimed character and its rule-defined interval, and is replaced/ended by the next applicable choice.
- Character changes and source death trigger immediate effect reevaluation.

The board shows compact current badges beside the character. Expanding a badge reveals source, start, expected end, elapsed game time, suspensions, resumptions, and end reason. Information panels snapshot all active abnormalities at send time. Historical effects remain queryable after ending.

## Persistent Ability State

The engine stores structured state for abilities whose result depends on earlier events, including at minimum:

- Fortune Teller red herring;
- Grandmother grandchild;
- Balloonist prior learned players/types;
- Philosopher acquired ability and drunk target;
- Cannibal current inherited ability;
- Juggler daytime guesses;
- once-per-game usage;
- Fang Gu jump usage;
- Po charge;
- Shabaloth prior targets;
- Pukka poisoned target chain;
- wake events for Chambermaid;
- nominations/votes/deaths required by retrospective information roles.

## Event Journal and Undo

Every state-changing action writes an immutable event with its inverse metadata and dependency links. Navigation does not touch the journal. An undo button belongs to the event/step that produced the state.

Before undo, the UI lists dependent events that must be reversed, such as information sent because of a transformation or an effect created by a later action. Undo is atomic: either the dependency chain reverses completely or nothing changes. Sent messages receive a retraction event; history never silently disappears.

## Vue Workflow

### Left column

Shows night number and an ordered list of only relevant action instances. Completed, current, skipped, undone, and upcoming states are visually distinct. Clicking a step inspects/navigates to it without reversing state.

### Center board

Shows canonical seats whether claimed or not. It distinguishes selected seat, acting seat, drafted targets, secret death, and active effects. Player presence is secondary metadata, never the basis for whether a character exists.

### Right task panel

Uses a fixed three-row layout:

1. fixed heading and step identity;
2. independently scrollable instructions, warnings, action controls, information, effects, and event history;
3. fixed bottom navigation bar.

The bottom bar always places Previous on the left, progress in the center, and Next/Dawn on the right. It has a fixed reserved height and remains in the same physical location regardless of description length; only the middle task content scrolls. Previous and Next/Dawn use stable-width button slots so label changes do not move either target. A reserved warning row immediately above it displays unresolved required work without shifting the buttons. On narrower layouts the same panel becomes the existing right drawer, pins the bar to the drawer bottom, and respects the safe-area inset.

When required work is unresolved, the first forward attempt presents the specific omissions and arms a `仍然继续` action. The storyteller may force progress; the journal records the forced skip and reason. No system validation may permanently trap the storyteller.

Selecting a seat temporarily replaces the task content with seat detail, but the fixed navigation bar remains available and the panel offers a clear return to the current task.

## Connectivity, Privacy, and Delivery

All writes use stable pending keys. Disconnection disables writes but preserves readable state and local inspection. Reconnection replaces authoritative state and retains selection when still valid.

Private identity, secret death, effects, truth annotations, and storyteller rationale never enter public views. A sent message records server acceptance and websocket delivery when observable; player acknowledgement is not required and cannot block the night.

## Official Chinese Data

The official editions use the official Simplified Chinese catalog, including `暗流涌动`, `黯月初升`, and `梦殒春宵`, and official names such as `贞洁者`, `猎手`, `镇长`, `红唇女郎`, `旅店老板`, `侍臣`, `弄臣`, `莽夫`, `僵怖`, `沙巴洛斯`, `卖花女孩`, `城镇公告员`, `女裁缝`, `镜像双子`, `诺-达鲺`, and `涡流`.

Canonical IDs remain stable so saved games and community manifests do not break. Community script display overrides are isolated from the official locale.

## Import Compatibility Boundary

The runtime accepts a normalized, versioned script pack produced by trusted built-in data or a future importer. JSON and PDF import are outside this slice, but the night engine may depend only on the normalized contract, never on a source-specific Python module.

Unknown custom characters remain visible and manually runnable with their imported instructions. Automatic actions require a known capability template or reviewed handler binding.

## Error Handling

- Invalid or stale actions return a domain error without partial mutation.
- Forced continuation is explicit and journaled.
- Undo validates dependency closure before mutation.
- Automatic information delivery falls back to storyteller review whenever truth is non-unique or a resolver is uncertain.
- Save migration retains the original file until the migrated state is validated and saved successfully.
- The UI surfaces command errors in the active task without moving navigation controls.

## Verification

Per the user's migration preference, implementation modules are completed before one consolidated verification phase. Final verification covers:

- legacy-save to canonical-seat migration, including unclaimed assigned seats;
- first/other-night queue generation using only in-play character instances;
- Lunatic-before-Demon ordering and target disclosure;
- conditional skips, secret deaths, death triggers, dawn publication, and source attribution;
- Pit-Hag normal, silent-failure, start-knowing, before/after-order, created-Demon, alignment, and undo cases;
- deterministic automatic information and adjudicated structured information;
- Drunk perceived-role timing and correct/incorrect review records;
- effect start, expiry, source loss, suspension, resumption, history, and information snapshots;
- backward navigation without mutation and dependency-aware explicit undo;
- offline/unclaimed seat proxy operation;
- fixed navigation position with short and long instructions at desktop and drawer widths;
- disconnected, pending, forced-skip, and websocket-refresh states;
- official Simplified Chinese catalog consistency;
- frontend suite/build, backend unit suite, Python compile, full smoke suite, and browser acceptance.
