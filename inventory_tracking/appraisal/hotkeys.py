"""The hotkey socket read on its own thread, so no poll of the service loop delays a macro key.

The loop used to read one datagram per pass, after every poll of the pass: a press waited for the
level map, the stash and the rune reads before it (59 passes of over half a second on 2026-10-11,
the worst 674 ms; teleport requests arrived 16 ms old on average, 4% over 100 ms, the worst 715 ms).
The macro's requests are handed to the runner the moment they arrive (it has its own lock); the
rest (Alt+D, the shop, the level map) wait in a queue for the loop, whose workers are its own.
"""

import queue
import socket
import threading
import time
from collections.abc import Callable

from inventory_tracking.common import LOG


class Hotkeys:
    def __init__(
        self,
        server: socket.socket,
        urgent: Callable[[bytes], bool],
        handle: Callable[[bytes, float], object],
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """`urgent(data)` says whether `handle(data, received)` takes the datagram on this thread."""
        self.server, self.urgent, self.handle, self.clock = server, urgent, handle, clock
        self.waiting: queue.Queue[bytes] = queue.Queue()
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self._listen, name='hotkeys', daemon=True)

    def start(self) -> None:
        self.thread.start()

    def _listen(self) -> None:
        while not self.stopped.is_set():
            try:
                data = self.server.recv(256)  # the socket's own timeout lets `close` be seen
            except TimeoutError:
                continue
            except OSError:
                return
            received = self.clock()
            if not self.urgent(data):
                self.waiting.put(data)
                continue
            try:
                self.handle(data, received)
            except Exception:
                LOG.exception('Hotkey failed')

    def get(self, timeout: float) -> bytes | None:
        """The next datagram for the loop, waited for up to `timeout` seconds (the loop's pace)."""
        try:
            return self.waiting.get(timeout=timeout)
        except queue.Empty:
            return None

    def wake(self) -> None:
        """End the loop's wait now: something it polls for has just changed."""
        self.waiting.put(b'')

    def close(self) -> None:
        self.stopped.set()
        if self.thread.is_alive():
            self.thread.join(timeout=1)
