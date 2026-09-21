from contextlib import contextmanager

from inventory_tracking.input.facade import InputError, Refused


class FakeFocus:
    def __init__(self, results=(True,)):
        self.results = list(results)

    def __call__(self, session):
        result = self.results.pop(0) if len(self.results) > 1 else self.results[0]
        if isinstance(result, Exception):
            raise result
        return result


class FakeKeyboard:
    """Script event results; retain enough lifecycle detail to test cleanup."""

    def __init__(self, *, results=(), held=False, display=True):
        self.results = list(results)
        self.held = held
        self.display = display
        self.events = []
        self.names = []
        self.connections = 0
        self.closed = 0
        self.open_ms = 0.25
        self.owner_pid = 1
        self.owner_checks = 0
        self.entry_error = None
        self.exit_error = None

    def keycodes(self, names):
        self.names = list(names)
        mapping = {b'Shift_L': 50, b'Control_L': 37, b'F3': 69, **{str(i).encode(): i + 9 for i in range(1, 5)}}
        codes = [mapping.get(name, 0) for name in names]
        return codes if all(codes) else None

    def focused_window_pid(self):
        self.owner_checks += 1
        return self.owner_pid

    def any_key_held(self):
        return self.held

    def _event(self, kind, key):
        self.events.append((kind, key))
        result = self.results.pop(0) if self.results else True
        if isinstance(result, Exception):
            raise result
        return result

    def press(self, key):
        return self._event('press', key)

    def release(self, key):
        return self._event('release', key)

    def sync(self):
        self.events.append(('sync', None))

    @contextmanager
    def connect(self):
        self.connections += 1
        if self.entry_error:
            raise self.entry_error
        try:
            yield self if self.display else None
        finally:
            self.closed += 1
            if self.exit_error:
                raise self.exit_error


class FakeDelivery:
    def __init__(
        self,
        *,
        clock=lambda: 100,
        refusal=None,
        late_refusal=None,
        error=None,
        on_send=None,
        on_entry=None,
        entry_error=None,
        exit_error=None,
    ):
        self.clock = clock
        self.refusal = refusal
        self.late_refusal = late_refusal
        self.error = error
        self.on_send = on_send
        self.on_entry = on_entry
        self.entry_error = entry_error
        self.exit_error = exit_error
        self.requests = []

    @contextmanager
    def attempt(self, target, request):
        if self.entry_error:
            raise self.entry_error
        if self.on_entry:
            self.on_entry()
        delivery = self

        class Attempt:
            refusal = delivery.refusal
            used = False
            active = True

            def send(self):
                if self.used or self.refusal or not self.active:
                    raise InputError('Attempt cannot send')
                self.used = True
                if delivery.late_refusal:
                    raise Refused(delivery.late_refusal)
                delivery.requests.append(request)
                if delivery.on_send:
                    delivery.on_send(request)
                if delivery.error:
                    raise delivery.error
                return delivery.clock()

        attempt = Attempt()
        try:
            yield attempt
        finally:
            attempt.active = False
            if self.exit_error:
                raise self.exit_error
