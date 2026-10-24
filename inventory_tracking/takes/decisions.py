"""Every decision of the macro, told to one listener: the combat take's `decision` events (2026-10-23,
rca/2026-10-23/realtime-3-findings.md).

The take used to copy the safety's last decision at the recorder's slow reads (record.py SLOW_SECONDS, 0.2 s,
deduped): a decision was up to 0.2 s late, one replaced within 0.2 s was never seen, and the fight loop's own looks
(hunt.py) were never recorded, so an act's age could only be bounded (rca/2026-10-23/realtime-2-findings.md §1).
With DECISION_EVENTS on, each look that decides tells `tell` once, on its own thread, right after it decides:

- the pursuit's (hunting/moves.py `pursue`): the safety's decision of that look, or for a look it did not price
  `{'looked_at', 'chosen', 'priced': False}`;
- the fight's (hunt.py, the strike's look): `{'looked_at', 'chosen': 'Strike', 'target', 'focal', 'look': 'fight'}`.

The recorder (record.py `Recorder.decided`) writes each as a `decision` event at the time it was told, and stops
copying the polled one. As input/sent.py: the listener must be a cheap append; one that raises is ignored.
"""

from collections.abc import Callable
from typing import Any


# 2026-10-23: False: the recorder copies the polled decision as before; nothing is told. On 2026-10-24 ~12:30 (gate5:
# 760 pairs, 745 identical, cs kills/s 0.815 -> 0.817, 0 deaths).
DECISION_EVENTS = True

Listener = Callable[[dict[str, Any]], None]

listener: Listener | None = None


def listen(found: Listener | None) -> Listener | None:
    """Make `found` the listener (None: nobody listens); the one before is returned."""
    global listener
    before, listener = listener, found
    return before


def tell(decision: dict[str, Any]) -> None:
    """A look's decision (a dict the teller no longer changes)."""
    found = listener
    if not DECISION_EVENTS or found is None:
        return
    try:  # ruff: ignore[suppressible-exception]
        found(decision)
    except Exception:
        pass


def fight(looked: float, decided: float, target: int, focal: tuple[float, float]) -> None:
    """The fight loop's choice (hunt.py `choose`) of the look begun at `looked`, made at `decided`: told as a
    `Strike` decision (its `ms` the choice's time from the look)."""
    if not DECISION_EVENTS or listener is None:
        return
    tell(
        {
            'looked_at': round(looked, 3),
            'ms': round(1000 * (decided - looked), 1),
            'chosen': 'Strike',
            'target': target,
            'focal': [round(focal[0], 1), round(focal[1], 1)],
            'look': 'fight',
        }
    )
