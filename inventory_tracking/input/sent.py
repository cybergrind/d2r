"""Every input this process sends, told to one listener: the combat take's `sent` events (2026-10-13).

The player's words: "the mouse moves were mine, I clicked by hand when we were need to organize inventory;
probably we could record mouse position?" A take records the pointer, its buttons and the keys down in every
frame; what it could not tell is who made a change. All the synthetic input of a process passes through two
places, and each tells `tell` after its send:

- keyboard.py `X11Connection`: `press`/`release` -> ('key', code, 1 or 0), `move_pointer` -> ('move', x, y)
  in root coordinates, `button` -> ('button', button, 1 or 0) (XTest);
- gamepad.py `Pad.event` -> ('pad', type, code, value) for each key or axis event (uinput; the reports are not
  told).

With no listener (the default, and always in `make osd`, which logs its own presses) a send costs a global read
and a test more. The listener is called on the sending thread right after the send: it must be a cheap append
that neither blocks nor does I/O (record.py `Recorder.sent`). One that raises is ignored: an input never fails
for being watched. Nothing here sends anything.
"""

from collections.abc import Callable


Listener = Callable[[str, tuple[int, ...]], None]

listener: Listener | None = None


def listen(found: Listener | None) -> Listener | None:
    """Make `found` the listener (None: nobody listens); the one before is returned."""
    global listener
    before, listener = listener, found
    return before


def tell(kind: str, *what: int) -> None:
    found = listener
    if found is None:
        return
    # The watcher's failure is never the input's. A bare try costs nothing until it raises (suppress would).
    try:  # ruff: ignore[suppressible-exception]
        found(kind, what)
    except Exception:
        pass
