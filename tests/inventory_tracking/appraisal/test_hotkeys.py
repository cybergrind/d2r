"""A macro key is handed over while the service loop is busy; the other hotkeys wait for the loop."""

import socket
import threading

from inventory_tracking.appraisal.hotkeys import Hotkeys


def test_a_macro_key_is_taken_while_a_poll_of_the_loop_still_runs(tmp_path):
    endpoint = tmp_path / 'service.sock'
    handled, taken = [], threading.Event()

    def handle(data, received):
        handled.append(data)
        taken.set()

    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as server:
        server.bind(str(endpoint))
        server.settimeout(0.05)
        keys = Hotkeys(server, lambda data: data.startswith(b'teleport '), handle)
        keys.start()
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as client:
                client.sendto(b'12.5', str(endpoint))
                client.sendto(b'teleport 12.5', str(endpoint))
            # The loop's thread is this one, and it is "in a slow poll": it reads nothing until the
            # macro key has been handled, which therefore did not wait for it.
            assert taken.wait(5)
            assert handled == [b'teleport 12.5']
            assert keys.get(1) == b'12.5'
            assert keys.get(0.01) is None
            keys.wake()  # the loop's wait ends with nothing to dispatch
            assert keys.get(5) == b''
        finally:
            keys.close()
    assert not keys.thread.is_alive()


def test_a_failing_handler_does_not_end_the_listening(tmp_path):
    endpoint = tmp_path / 'service.sock'
    seen, second = [], threading.Event()

    def handle(data, received):
        seen.append(data)
        if len(seen) == 1:
            raise RuntimeError('boom')
        second.set()

    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as server:
        server.bind(str(endpoint))
        server.settimeout(0.05)
        keys = Hotkeys(server, lambda data: True, handle)
        keys.start()
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as client:
                client.sendto(b'a', str(endpoint))
                client.sendto(b'b', str(endpoint))
            assert second.wait(5)
        finally:
            keys.close()
