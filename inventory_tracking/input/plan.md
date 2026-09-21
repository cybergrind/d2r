# Input sub-module implementation plan

2026-09-21. Executes [design.md](design.md) with its review suggestions resolved.
Where this plan and the design body disagree, this plan wins; step 0 folds the
resolutions back into the design. Nothing here is implemented yet.

Rules for every step: red/green per [development.md](../../development.md), then
`uv run pytest tests -q`, `uv run pre-commit run --all-files` (ruff, pyrefly).
Default thresholds, cooldowns, OSD text and the guard set do not change until the
roadmap steps. Commit only when asked.

## Resolved contract

### Types

```python
# models.py — next to Outcome, so PotionResult can carry it without importing the package
class Refusal(StrEnum):
    UNFOCUSED = 'unfocused'; NO_DISPLAY = 'no_display'; UNKNOWN_KEY = 'unknown_key'
    KEY_HELD = 'key_held'; STALE = 'stale'

@dataclass(frozen=True)
class PotionResult:
    outcome: Outcome
    event: PotionSent | None = None
    reason: Refusal | None = None       # only with Outcome.REJECTED

# inventory_tracking/input/facade.py
@dataclass(frozen=True)
class Target:
    session: SessionIdentity
    sampled_at: float
    max_age: float

class Refused(Exception):
    """Clean refusal after entry: no key event was attempted."""
    def __init__(self, refusal: Refusal) -> None: ...

class InputError(RuntimeError):
    """Uncertain: a key may be down, a release was unconfirmed, or the backend failed unexpectedly."""

class Attempt(Protocol):
    refusal: Refusal | None
    def send(self) -> float: ...

class Delivery(Protocol):               # what PotionsController depends on
    def attempt(self, target: Target, request: PotionRequest) -> AbstractContextManager[Attempt]: ...

class PotionInput:                      # implements Delivery
    def __init__(self, config: InputConfig = INPUT, *, clock=time.monotonic, sleep=time.sleep,
                 focus: FocusProbe | None = None, keyboard: Keyboard | None = None) -> None: ...
```

### Facade behaviour

Entry (`attempt().__enter__`), in this order, each stopping at the first failure
and setting `attempt.refusal` without raising: open the display (`NO_DISPLAY`),
resolve keycodes for `bindings.keys_for(config, request)` (`UNKNOWN_KEY`), focus
(`UNFOCUSED`), held keys (`KEY_HELD`), age by the injected clock (`STALE`). No key
event is emitted on entry. `send()` re-checks focus, held keys and age; a failure
raises `Refused(refusal)` before any key event. It then presses in order, syncs,
`sleep(key_hold_seconds)`, releases in reverse order, syncs, and returns
`clock()` taken after the final sync. A press returning false, a release returning
false or raising, and any other exception after the first key-down become
`InputError` (release is still attempted for every pressed key). A second `send()`
and `send()` on a refused attempt raise `InputError`. Exit closes the display;
any unexpected exception on entry or exit is re-raised as `InputError`. Only
`Refused` and `InputError` escape the facade.

### Controller behaviour (`PotionsController._deliver`)

Under the still-held ledger lock, with `now` from the decision:

1. `cooldowns[key] = now`, `transaction.save()`. Unchanged: clean refusals still
   reserve the attempt cooldown.
2. `previous = (record.pending, data.last_delivery)`.
3. `with delivery.attempt(Target(state.session, state.sampled_at, sample_max_age), request) as attempt:`
   - `attempt.refusal` set: remember it, leave the block.
   - Otherwise `reserved_at = clock()` (a fresh reading, not `now`);
     `cooldowns[key] = reserved_at`; `record.pending = PendingReservation(item_id, reserved_at)`;
     `data.last_delivery = LastDelivery(core, reserved_at)`; `transaction.save()`.
     A save failure propagates: nothing is pressed, the transaction exits failed,
     `step()` reports `UNAVAILABLE` as for any ledger error today.
   - `finished_at = attempt.send()`. On `Refused`: restore `previous`,
     `transaction.save()`, remember the refusal. No rollback is ever attempted for
     `InputError`.
4. The whole `with` (entry, body, exit) sits in `try/except InputError`: mark
   `record.suspended = True`, log with traceback, return `SUSPENDED`. The
   transaction's normal exit persists the suspension.
5. After the block, a remembered refusal returns `PotionResult(REJECTED, reason=refusal)`.
   Otherwise `pending.sent_at = last_delivery.at = finished_at` and
   `PotionResult(SENT, PotionSent(request, finished_at))`. A failure of the final
   save in the transaction exit surfaces as `UNAVAILABLE`; the reservation saved in
   step 3 remains the recovery guard.

Behaviour differences from today, all intended: a late refusal (focus lost, key
held, sample aged between entry and key-down) is `REJECTED` with its reason and
does not suspend; `REJECTED` carries a reason; the rest of the ledger timeline is
identical.

### Bindings

```python
class InputConfig(Config):
    game_app_id: str = 'steam_app_2536520'
    focus_timeout: Positive = 0.3
    key_hold_seconds: Positive = 0.025
    bindings: Mapping[Actor, tuple[str, ...]] = {Actor.PLAYER: (), Actor.MERC: ('Shift_L',)}
    column_keys: Mapping[int, str] = {1: '1', 2: '2', 3: '3', 4: '4'}
```

Validators: `bindings` names every actor; `column_keys` has exactly the keys 1–4;
every name is non-empty; both are frozen with `MappingProxyType` and serialized
back to plain dicts, as `HealingConfig` does. `bindings.keys_for(config, request)`
returns `(*bindings[actor], column_keys[column])` as key names; the facade encodes
them for `keycodes()`.

## Steps

### 0. Settle the design

Edit `design.md`: replace the facade contract, the controller sketch and the
"exactly as today" claim with the resolved contract above; add `column_keys`;
rewrite roadmap step 2 with the focus-tracker rules from step 6 below; remove the
review section (its items are resolved here). Link this plan from the design and
the tracking README. No code.

### 1. Move, no behaviour change

- `git mv inventory_tracking/{focus,keyboard,potion_input}.py inventory_tracking/input/`;
  fix relative imports to `..config`, `..models`, `..linux_process`.
- `inventory_tracking/input/__init__.py` re-exports `PotionInput`.
- `inventory_tracking/potion_input.py` becomes `from .input.facade import PotionInput`
  (deleted in step 2). `osd/__main__.py` imports from `..input`.
- Move tests to `tests/inventory_tracking/input/{test_facade,test_focus,test_keyboard}.py`;
  patch targets become `inventory_tracking.input.focus.subprocess.check_output`
  and `inventory_tracking.input.facade.time.sleep`. Add `tests/inventory_tracking/input/__init__.py`.
- Runbook module table (`osd/README.md`) lists the package instead of three files.

Verify: suite green with no test body changes beyond import paths.

### 2. The facade and the controller switch

Red first, in `tests/inventory_tracking/input/test_facade.py` (rewrite, keep
`FakeKeyboard`; add `FakeFocus(results=...)`, a `clock` list-scripted like today's
`Mock(side_effect=...)`, and `sleep` that appends `('hold', None)` to the event log):

- entry refusal per cause: display, unknown key, focus, held, stale; assert
  `refusal` value, zero press events, connection closed at exit.
- send sequence per actor: presses, sync, hold, releases reversed, sync;
  `send()` returns the clock reading taken after the last sync.
- late refusal per cause raises `Refused` with zero press events.
- failed press → both releases attempted, `InputError`; failed release → remaining
  releases attempted, `InputError`; `sleep` raising → releases, `InputError`.
- second `send()` and `send()` after refusal raise `InputError`.
- an exception from `keyboard.connect()` surfaces as `InputError`.

Red second, in `tests/inventory_tracking/test_potions.py` and `conftest.py`:

- `FakeDelivery` in `conftest.py`: constructor takes `refusal=None`,
  `late_refusal=None`, `error=None`, `on_send=None`; records `requests`; its
  `Attempt.send` calls `on_send()` (tests advance the clock there), then raises
  `Refused`/`InputError` or returns `clock()`. `healing_setup` keeps returning
  `(make, sent)` with `sent` called from `on_send`, so existing tests change only
  in how they script the fake (`controller.potions.delivery = FakeDelivery(...)`).
- New cases: entry refusal → `REJECTED` with reason, cooldown kept, no pending;
  late refusal → `REJECTED`, pending and last-delivery restored, cooldown kept,
  next instance is not suspended; `InputError` after press → `SUSPENDED` and
  a fresh instance stays suspended (today's partial-delivery test, re-scripted);
  `InputError` on exit after a successful send → `SUSPENDED`, no `SENT` event;
  delayed entry: clock advances between decision and reservation, the cooldown is
  measured from the reservation; sample during delivery stays `STALE_BELT`.
- `tests/inventory_tracking/input/test_contract.py`: parametrized over the real
  facade with fakes and over `FakeDelivery`; asserts the invariants above.
  `test_automation.py::test_rejected_input_does_not_create_notification` and
  `osd/test_main.py` switch to the new fake or patch target.

Green:

- `models.py`: `Refusal`, `PotionResult.reason`.
- `input/facade.py`: `Target`, `Refused`, `InputError`, `Attempt`, `Delivery`,
  `PotionInput.attempt`; `sleep` injected now, since the tests are rewritten anyway
  (design step 4 folds in here). `__call__` and `time.sleep` are deleted.
- `potions.py`: `Delivery` replaces `type Deliver`; `_deliver` per the resolved
  contract; drop the `nonlocal` callback and the "omitted delivery reservation" checks.
- Delete `inventory_tracking/potion_input.py`.
- Runbook: `<actor>-heal.json` gains `reason`; the guard paragraph mentions that
  a late focus loss rejects instead of suspending.

Verify: suite green; `uv run -m inventory_tracking.osd --demo --once` unchanged.

### 3. Bindings in config

Red: `test_config.py` (defaults, missing actor, wrong column set, empty name, frozen
mappings, `with_overrides` round trip); `test_facade.py` (a non-digit column key
and a changed merc modifier drive the actual keycode names; defaults unchanged).
Green: `InputConfig` fields and validators; `input/bindings.py` with `keys_for`;
facade uses it. Runbook `INPUT` line names both mappings.

### 4. Check CLI

`inventory_tracking/input/__main__.py`: `uv run -m inventory_tracking.input --check [--pid N]`.
Finds the game through `linux_process.find_game_processes()` unless pinned, builds
a `Target` with the current clock, enters one `attempt` for each actor and column
and prints per line: focused app id, X11 owner pid and identity match, keycode per
bound name, held keys, and the resulting refusal or `ready`. Never calls `send()`.
Exit 0 only when every attempt is `ready`. Test: a fake keyboard/focus run through
the argument parser, asserting the report lines and exit codes. Runbook gains the
command under diagnostics. This is the host smoke test for every later step.

### 5. Roadmap 1 — drop `xdotool`

- `X11Connection.focused_window_pid() -> int | None`: `XGetInputFocus`, then walk
  the window and its ancestors via `XQueryTree` (bounded to 16 levels, as
  `xdotool getwindowfocus` climbs to a client window) reading `_NET_WM_PID`
  through `XInternAtom` + `XGetWindowProperty`, freeing with `XFree`. Declare the
  new signatures in `X11Keyboard.libraries`.
- `focus.py`: `NiriFocusProbe` keeps only the `niri msg --json focused-window`
  query; `owns_process(pid, session)` keeps `is_game` and `identity` exact match.
  The facade composes: Niri app id, then `keys.focused_window_pid()` against the
  target session, on the connection it already holds.
- Tests: ctypes mocks for the new calls including the ancestor walk and a window
  without the property; facade focus tests through `FakeKeyboard.owner_pid`.
- Host verification before removing `xdotool` from the runbook: `--check` prints
  the X11 owner pid; the user compares it with `xdotool getwindowfocus getwindowpid`
  while the game is focused and while a terminal is focused.

### 6. Roadmap 2 — `FocusTracker`

Rules (replacing the design's one-second age rule):

- A daemon thread runs `niri msg --json event-stream` and consumes lines with a
  `select`-based loop that wakes at least every 0.25 s; each wake stamps
  `alive_at`. Focus is cached as `app_id | None` from `WindowFocusChanged` and the
  initial `WindowsChanged` snapshot, with `ready = True` once both initial events
  arrived. Unchanged focus stays valid indefinitely.
- `focused(session)` is a lookup that returns `app_id == game_app_id` only when
  `ready` and `alive_at` is within 1 s (the thread is being scheduled); otherwise
  it falls back to `NiriFocusProbe` for that call. The X11 owner check from step 5
  runs on every attempt regardless.
- EOF, process exit, a non-JSON line or an unknown shape clears the cache and
  `ready`, and reconnects with backoff 0.5 s doubling to 5 s; a fresh initial
  snapshot is required before the cache is trusted again.
- Tests feed recorded lines through a fake pipe: initial snapshot then silence for
  minutes stays focused; focus change to another app refuses; EOF invalidates and
  the fallback probe is consulted; reconnection re-arms only after the snapshot;
  a stalled reader (no `alive_at` progress) falls back.
- Host verification: `--check` shows the tracker state and app id; the runbook
  records the observed switch latency.

### 7. Roadmap 3 — connection reuse

Only if `--check` timings after steps 5–6 show `XOpenDisplay` above a few
milliseconds. Keep one display for the facade's lifetime, reopen on any X error,
still scoped so `attempt` exit never leaves a key down. Otherwise close this item
as not needed in the runbook.

## Files touched per step

| Step | Production | Tests | Docs |
|---|---|---|---|
| 0 | — | — | `input/design.md`, `README.md` |
| 1 | `input/{__init__,facade,focus,keyboard}.py`, `potion_input.py` shim, `osd/__main__.py` | `tests/inventory_tracking/input/*` | `osd/README.md` table |
| 2 | `models.py`, `input/facade.py`, `potions.py`, delete `potion_input.py` | `test_facade.py`, `test_contract.py`, `test_potions.py`, `conftest.py`, `test_automation.py`, `osd/test_main.py` | `osd/README.md` guards, heal.json |
| 3 | `config.py`, `input/bindings.py`, `input/facade.py` | `test_config.py`, `test_facade.py`, `test_bindings.py` | `osd/README.md` INPUT |
| 4 | `input/__main__.py` | `tests/inventory_tracking/input/test_main.py` | `osd/README.md` diagnostics |
| 5 | `input/keyboard.py`, `input/focus.py`, `input/facade.py` | `test_keyboard.py`, `test_focus.py`, `test_facade.py` | runbook dependencies |
| 6 | `input/focus.py` (`FocusTracker`) | `test_focus.py` | runbook diagnostics |
| 7 | `input/keyboard.py` | `test_keyboard.py` | runbook |

Steps 0–4 are one uninterrupted refactoring pass verifiable by the suite plus a
demo run. Steps 5–7 each need the user's host verification through `--check`
before the next one starts.
