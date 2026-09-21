# Input sub-module design

Implemented and host-verified, 2026-09-21. Native X11 ownership and FocusTracker
passed their host gates; connection reuse was measured and closed as unnecessary.
The step order and the resolved contract are in the [implementation plan](plan.md). Companion to the
[widget contracts](../osd/design.md); operational defaults stay in the
[runbook](../osd/README.md).

## Goal

Move everything that touches the compositor, the X server and the keyboard into
one package, `inventory_tracking/input/`, behind a single facade. Healing policy
(`potions.py`, `heal.py`) depends on that facade only. Performance work (focus
tracking, subprocess removal, connection reuse) and low-level detail (XTest, Niri
IPC, future backends) then change inside the package, and the controllers and
their tests do not move.

## Before migration

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
  __init__.py     exports PotionInput, Target, Refusal, Refused, InputError, Attempt, Delivery
  __main__.py     guard-only --check with optional atomic report
  facade.py       PotionInput: attempt() → Attempt; owns guards and the key sequence
  bindings.py     PotionRequest → key names, from InputConfig.bindings and column_keys
  focus.py        FocusTracker heartbeat/reconnect; NiriFocusProbe fallback; owns_process
  keyboard.py     Keyboard / KeyConnection protocols; X11Keyboard, X11Connection
tests/inventory_tracking/input/
  fakes.py        FakeKeyboard, FakeFocus, FakeDelivery
  test_facade.py  test_contract.py  test_main.py  test_focus.py  test_keyboard.py
```

`InputConfig` stays in `config.py` with the other configs and gains frozen `bindings` and `column_keys`.
Nothing outside the package imports `focus`, `keyboard` or `bindings`.

## Facade contract

### Types

```python
# models.py — next to Outcome, so PotionResult can carry it without importing the package
class Refusal(StrEnum):
    UNFOCUSED = 'unfocused'
    NO_DISPLAY = 'no_display'
    UNKNOWN_KEY = 'unknown_key'
    KEY_HELD = 'key_held'
    STALE = 'stale'


@dataclass(frozen=True)
class PotionResult:
    outcome: Outcome
    event: PotionSent | None = None
    reason: Refusal | None = None  # only with Outcome.REJECTED


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


class Delivery(Protocol):  # what PotionsController depends on
    def attempt(self, target: Target, request: PotionRequest) -> AbstractContextManager[Attempt]: ...


class PotionInput:  # implements Delivery
    def __init__(
        self,
        config: InputConfig = INPUT,
        *,
        clock=time.monotonic,
        sleep=time.sleep,
        focus: FocusProbe | None = None,
        keyboard: Keyboard | None = None,
    ) -> None: ...
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
any unexpected exception on entry or exit is re-raised as `InputError`. Backend exceptions escape only as `Refused` or `InputError`; caller-body
exceptions such as ledger save failures propagate unchanged.

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

A late refusal (focus lost, key held, sample aged between entry and key-down) is `REJECTED` with its reason and
does not suspend. The old final guards already refused before reservation; the
new explicit `Refused` path preserves this distinction after moving reservation
between entry and send. `REJECTED` now carries a reason; the ledger timeline is
otherwise preserved.

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

## Performance roadmap, all inside the package

Ordered by payoff over risk. Each step is host-verified before the next; none
changes the facade.

1. **Drop `xdotool`.** The X11 owner check reads `_NET_WM_PID` of the window
   returned by `XGetInputFocus` on the connection the attempt already holds. The
   Niri `app_id` query stays: X focus alone cannot see a Wayland-native window
   taking over. Saves two subprocess spawns per delivery.
2. **`FocusTracker` over `niri msg --json event-stream`.** A daemon uses a
   select loop waking at least every 0.25 s to stamp `alive_at`. Trust the cached
   app id only after the complete WindowsChanged snapshot (which includes
   `is_focused`) and while that heartbeat is within 1 s. Niri's
   [state implementation](https://raw.githubusercontent.com/YaLTeR/niri/main/niri-ipc/src/state.rs)
   sends no separate initial WindowFocusChanged; subsequent focus events update
   the initialized snapshot. Unchanged focus stays valid indefinitely.
   Otherwise use the one-shot probe. EOF, process exit, malformed JSON or unknown
   event shape clears readiness and reconnects with 0.5 s backoff doubling to 5 s;
   a fresh initial snapshot is required. Check exact X11 ownership on every attempt,
   regardless of cache health. Verify long silence, switching, reconnect and stalled
   reader fallback; record host switch latency through `--check`.
3. **Reuse the X connection** for the facade's lifetime, reopening on error, if
   `XOpenDisplay` shows up in timings after 1 and 2. Closed as unnecessary on
   2026-09-21: median 0.130 ms, p95 0.296 ms over 1,560 host checks.
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
- `FocusTracker` tests feed protocol-shaped event-stream lines through pipes and assert heartbeat health, long quiet focus, reconnection
  and fallback. `X11Keyboard` tests keep the current ctypes stubs.
- No test monkeypatches `time`; `clock` and `sleep` are injected.

## Migration

Follow the [implementation plan](plan.md): settle this contract, move the modules,
switch the facade/controller together (including injected sleep), configure actor
and column bindings, then add the guard-only check CLI. Steps 0–4 are verified by
the suite and demo. Roadmap steps 5–7 each require host verification before the
next step. Default thresholds, cooldowns, OSD text and guards remain unchanged.

## Non-goals

Menu detection (excluded by user authorization), Wayland-native injection (the
game runs under XWayland), any change to healing policy or ledger schema.
