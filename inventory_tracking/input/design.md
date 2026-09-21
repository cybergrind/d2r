# Input sub-module design

Proposal, 2026-09-21. Not implemented; the step order and the resolved contract
are in the [implementation plan](plan.md). Companion to the
[widget contracts](../osd/design.md); operational defaults stay in the
[runbook](../osd/README.md).

## Goal

Move everything that touches the compositor, the X server and the keyboard into
one package, `inventory_tracking/input/`, behind a single facade. Healing policy
(`potions.py`, `heal.py`) depends on that facade only. Performance work (focus
tracking, subprocess removal, connection reuse) and low-level detail (XTest, Niri
IPC, future backends) then change inside the package, and the controllers and
their tests do not move.

## Today

`potion_input.py`, `focus.py` and `keyboard.py` sit at the package top level.
`PotionsController` calls `deliver(state, request, max_age=..., before_send=...)`
and receives a `bool`. The controller learns what happened through that bool, a
`before_send` callback that mutates two `nonlocal` variables, exceptions, and a
runtime assertion that the callback was invoked. `PotionInput` receives the whole
`State` and re-runs guards the controller already applied to the same object.
The merc's `Shift_L` modifier and the column digits are hard-coded.

Each delivery runs `niri msg` and `xdotool` twice (focus is checked before opening
the display and again before key-down), each with a 0.3 s timeout, plus a 25 ms
hold, all synchronously on the reader thread. Deliveries are cooldown-gated, so
samples without a delivery pay nothing; a sample with two deliveries can spend
over a second in subprocesses, delaying the very read that acknowledges
consumption.

## Package layout

```
inventory_tracking/input/
  __init__.py     re-exports the facade: PotionInput, Target, Refusal, InputError
  facade.py       PotionInput: attempt() → Attempt; owns guards and the key sequence
  bindings.py     PotionRequest → key names, from InputConfig.bindings
  focus.py        FocusProbe protocol; NiriX11FocusProbe (today's probe); later FocusTracker
  keyboard.py     Keyboard / KeyConnection protocols; X11Keyboard, X11Connection
tests/inventory_tracking/input/
  conftest.py     FakeKeyboard, FakeFocus, FakeDelivery
  test_facade.py  test_bindings.py  test_focus.py  test_keyboard.py
```

`InputConfig` stays in `config.py` with the other configs and gains `bindings`.
Nothing outside the package imports `focus`, `keyboard` or `bindings`.

## Facade contract

The facade separates *may I press* from *press*, so the controller writes its
reservation between the two in straight-line code.

```python
@dataclass(frozen=True)
class Target:
    """What a guard needs from a sample. Nothing else crosses the boundary."""
    session: SessionIdentity
    sampled_at: float
    max_age: float


class Refusal(StrEnum):
    UNFOCUSED = 'unfocused'      # compositor focus or X11 owner is not this game process
    NO_DISPLAY = 'no_display'    # XOpenDisplay failed
    UNKNOWN_KEY = 'unknown_key'  # a bound key name has no keycode
    KEY_HELD = 'key_held'        # the player is physically holding a key
    STALE = 'stale'              # the sample aged past max_age before key-down


class InputError(RuntimeError):
    """A key may still be down, or a release was not confirmed. Caller must suspend."""


class Attempt(Protocol):
    refusal: Refusal | None       # set on entry; when set, send() is not allowed
    def send(self) -> float: ...  # re-checks focus/held/stale, presses, holds, releases; returns sent_at


class PotionInput:
    def __init__(self, config: InputConfig = INPUT, *, clock=time.monotonic, sleep=time.sleep,
                 focus: FocusProbe | None = None, keyboard: Keyboard | None = None) -> None: ...
    def attempt(self, target: Target, request: PotionRequest) -> AbstractContextManager[Attempt]: ...
```

Controller side, replacing `_deliver`'s callback:

```python
with self.input.attempt(Target(session, state.sampled_at, self.config.sample_max_age), request) as attempt:
    if attempt.refusal:
        return PotionResult(Outcome.REJECTED, reason=attempt.refusal)
    record.pending = PendingReservation(item_id=item.item_id, sent_at=now)
    data.last_delivery = LastDelivery(session=record.session.core, at=now)
    transaction.save()                       # on disk before the first key-down
    try:
        sent_at = attempt.send()
    except Exception:
        record.suspended = True
        LOG.exception('%s healing suspended after input error', actor)
        return PotionResult(Outcome.SUSPENDED)
```

`send()` may still refuse (focus lost or key held in the window between entry and
key-down). It then raises `Refused(refusal)`, a subclass of `InputError`, and the
controller suspends exactly as today: a reservation exists, so the outcome is
uncertain. The ledger lock stays held across the whole `with`, as now, because the
reservation must be durable before the press.

### Invariants the facade guarantees

- Entering an `attempt` performs no key events. A refusal is side-effect free.
- `send()` is called at most once per attempt; a second call raises.
- `send()` releases every key it pressed, in reverse order, even when a press or
  the hold raises. If any release is not confirmed it raises `InputError`.
- The X connection opens on entry and closes on exit of the `with`, never earlier.
- All timing goes through the injected `clock` and `sleep`; the package never
  calls `time` directly.
- The facade never reads the ledger, the belt, health or cooldowns. It receives a
  fully resolved `PotionRequest` and a `Target`.

### Guards and who owns them

The set of conditions that must hold before a key-down is unchanged; only
duplication goes. Conditions that cannot change between decision and press stay
with the controller, which already checks them against the same `State`: actor is
valid, column is 1–4, the cell is usable stock, the player is alive, the sample
is fresh at decision time. Conditions that can change in that window belong to
the facade and are checked at entry and again immediately before key-down: the
game process owns compositor and X11 focus, no key is physically held, the sample
has not aged past `max_age` by the injected clock.

### Bindings

`InputConfig.bindings: Mapping[Actor, tuple[str, ...]]` holds modifier key names,
default `{PLAYER: (), MERC: ('Shift_L',)}`; the column digit is appended by
`bindings.keys_for(request)`. The validator requires every actor. Rebinding the
in-game potion keys becomes a config change, and tests assert the mapping through
config instead of through the sequence.

## Performance roadmap, all inside the package

Ordered by payoff over risk. Each step is host-verified before the next; none
changes the facade.

1. **Drop `xdotool`.** The X11 owner check reads `_NET_WM_PID` of the window
   returned by `XGetInputFocus` on the connection the attempt already holds. The
   Niri `app_id` query stays: X focus alone cannot see a Wayland-native window
   taking over. Saves two subprocess spawns per delivery.
2. **`FocusTracker` over `niri msg --json event-stream`.** A daemon thread keeps
   the focused `app_id` and the time it was observed. `focused()` becomes a lookup
   that refuses when the stream is disconnected or older than a bound (start at
   1 s). Falls back to the one-shot probe when the stream cannot start. Saves the
   remaining two spawns and removes the 0.3 s worst case from the reader thread.
3. **Reuse the X connection** for the facade's lifetime, reopening on error, if
   `XOpenDisplay` shows up in timings after 1 and 2. Probably unnecessary.
4. **Off-thread delivery** is deliberately not planned. The reservation must be
   written under the ledger lock before key-down, and moving the press to a worker
   would hold the lock across threads or split the transaction. After steps 1–2
   a delivery costs about the 25 ms hold, which the reader thread can afford.

## Diagnostics

- `PotionResult` gains `reason: Refusal | None`, published in `<actor>-heal.json`,
  so "why did nothing happen" is answerable from the run directory.
- `uv run -m inventory_tracking.input --check` runs the guards once without
  pressing: focused app id, X11 owner match, keycodes for every binding, held keys.
  This is the host-side smoke test for steps 1–3 and for new compositor versions.

## Testing

- Facade tests use `FakeKeyboard` and `FakeFocus` and assert observable sequences:
  order of press/hold/release, guaranteed release on a failing press, refusal
  before any event, at-most-once `send`, connection closed on exit.
- Controller tests use `FakeDelivery`, a scripted `Attempt` factory. A contract
  test parametrized over the real facade with fakes and over `FakeDelivery`
  keeps the fake honest on the invariants above.
- `FocusTracker` tests feed recorded event-stream lines and assert staleness
  refusal and fallback. `X11Keyboard` tests keep the current ctypes stubs.
- No test monkeypatches `time`; `clock` and `sleep` are injected.

## Migration

1. Create the package; move `focus.py`, `keyboard.py`, `potion_input.py` and their
   tests; keep `inventory_tracking.potion_input` as a one-line re-export for one
   step. Green, no behavior change.
2. Add `attempt()` beside `__call__`; switch `PotionsController._deliver` to it;
   delete `__call__`, the `before_send` callback, the `nonlocal` state and the
   "omitted delivery reservation" checks; add `reason` to `PotionResult`. Update
   `test_potions.py` to `FakeDelivery`.
3. Add `InputConfig.bindings` and `bindings.py`; remove the hard-coded names.
4. Inject `sleep`; remove the `time.sleep` monkeypatches from tests.
5. Roadmap steps 1–3, each with `--check` output recorded in the runbook.

Steps 1–4 keep default thresholds, cooldowns, OSD text and the guard set
unchanged and are verifiable by the existing test suite plus one demo run.

## Non-goals

Menu detection (excluded by user authorization), Wayland-native injection (the
game runs under XWayland), any change to healing policy or ledger schema.

## Review suggestions — 2026-09-21

The proposal above is still a draft. Resolve the following before implementation;
the controller sketch and stream-age rule above must not be copied as-is.

1. **Separate focus state from stream health.** Niri sends an initial snapshot
   followed by change events; it does not promise a periodic focus heartbeat
   ([event-stream contract](https://niri-wm.github.io/niri/niri_ipc/enum.Request.html#variant.EventStream)).
   Unchanged focus must remain valid beyond one second. Track initialization,
   connection state and reader health separately from the last focus change.
   Invalidate cached focus on EOF, process exit or an unreadable state update;
   reconnect with bounded backoff and require a fresh initial snapshot before
   trusting the cache again. Specify how reader lag is detected rather than
   treating silence as failure. Keep the exact X11 process-identity check on
   every attempt. Test long periods without events, focus loss, disconnect and
   reconnection. Startup fallback remains explicit and must retain all guards.

2. **Spell out the complete ledger timing contract.** Preserve the current
   cooldown write before attempting input, including clean entry refusals.
   Read the clock again when creating the durable reservation, and refresh the
   cooldown then; do not reuse the earlier decision-time `now`. Define the
   successful `send()` timestamp as completion after release and synchronization.
   After successful context exit, advance both `pending.sent_at` and
   `last_delivery.at` to that completion timestamp and emit `PotionSent` with
   the same value. Preserve the existing tests for rejected-attempt cooldowns
   and samples taken during delivery; add a delayed-entry case to ensure the
   cooldown is measured from reservation rather than the initial decision.

3. **Handle the entire attempt lifecycle inside the ledger transaction.** Put
   the exception boundary around entry, `send()` and context exit, not just
   `send()`. Return success only after cleanup succeeds. Represent expected
   pre-input refusals explicitly; preserve suspension for unexpected input
   errors, including cleanup failures after a press. Catch those failures
   inside the transaction so its normal exit can persist suspension. A failed
   reservation save must prevent sending; a failed final save must not report
   success, and the already-persisted reservation remains the recovery guard.
   Test entry, send and exit failures, including restart behavior after a
   post-press cleanup error.

4. **Distinguish a clean refusal from uncertain delivery.** Make `Refused` a
   separate exception from `InputError`, with a strict guarantee that no key
   event was attempted. Catch it inside the attempt context, but finalize its
   result only after successful context exit. Under the still-held ledger lock,
   restore the previous pending and last-delivery values, retain the attempt
   cooldown, persist the rollback, and return `REJECTED` with its reason. Never
   roll back after a press was attempted or cleanup failed; those paths remain
   suspended. A crash before rollback leaves the durable reservation in place.
   Test focus loss, a held key and sample expiry between entry and sending;
   these must cause no key events and no permanent suspension after successful
   rollback. The draft's claim that these cases suspend "exactly as today" is
   incorrect: today's final guards reject before creating the reservation.

5. **Configure column keys as well as actor modifiers.** Keep actor bindings
   for modifiers, and add `InputConfig.column_keys: Mapping[int, str]` with
   defaults `{1: '1', 2: '2', 3: '3', 4: '4'}`. Resolve modifiers followed by the
   configured column key. Validate exactly columns 1–4, every actor and nonempty
   key names; freeze both mappings like the existing configuration mappings.
   Resolve keycodes before reserving, returning `UNKNOWN_KEY` for an unresolved
   name. Test a non-digit column binding and a changed merc modifier through
   actual fake-keyboard sequences, as well as unchanged defaults. Include both
   mappings in migration step 3 and the `--check` diagnostics.
