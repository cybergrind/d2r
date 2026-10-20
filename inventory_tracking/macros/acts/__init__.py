"""The terrorized acts' orders, one script per act (routes/act-terrorize-plan.md §11; how to add one: README.md here).

`SCRIPTS`: act -> its `ActScript` (macros/acts/act<N>.py `SCRIPT`). An act's kind (loop.py `ACT_KINDS`) is offered
once its script is `ready`; until then its kind is "coming" on the KP_6 picker and the act, terrorized by hand, is
played by tzroutine.py's generic boss-first order.
"""

from inventory_tracking.macros.acts import act1, act2, act3, act4, act5
from inventory_tracking.macros.acts.engine import ActScript


SCRIPTS: dict[int, ActScript] = {
    1: act1.SCRIPT,
    2: act2.SCRIPT,
    3: act3.SCRIPT,
    4: act4.SCRIPT,
    5: act5.SCRIPT,
}


def script_of(act: int) -> ActScript | None:
    """Act `act`'s script; None for no act 1-5."""
    return SCRIPTS.get(act)


def ready(act: int | None) -> bool:
    """Whether act `act`'s script is ready (its kind offered, its order played)."""
    script = SCRIPTS.get(act) if act is not None else None
    return script is not None and script.ready
