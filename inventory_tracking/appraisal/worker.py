"""Freeze requests before asynchronous evidence retrieval; publish newest only."""

import math
import threading


class AppraisalWorker:
    def __init__(self, capture, retrieve, publish, executor):
        self.capture, self.retrieve, self.publish, self.executor = capture, retrieve, publish, executor
        self.lock = threading.Lock()
        self.generation = 0
        self.last_request = -math.inf
        self.future = None

    def request(self, requested_at, now):
        if not math.isfinite(requested_at) or not 0 <= now - requested_at <= 1 or now - self.last_request < 0.35:
            return False
        with self.lock:
            self.last_request = now
            self.generation += 1
            request_id = self.generation
            if self.future:
                self.future.cancel()
            self.publish({'request_id': request_id, 'state': 'pending'})
        try:
            frozen = self.capture.freeze()
        except Exception as exc:
            diagnostics = getattr(exc, 'diagnostics', None)
            self.deliver(
                request_id,
                {
                    'state': 'rejected',
                    'reason': str(exc),
                    **({'diagnostics': diagnostics} if diagnostics is not None else {}),
                },
            )
            return True
        self.deliver(request_id, {'state': 'captured', 'frozen': frozen})
        self.future = self.executor.submit(self.finish, request_id, frozen)
        return True

    def deliver(self, request_id, result):
        with self.lock:
            if request_id != self.generation:
                return False
            self.publish({'request_id': request_id, **result})
            return True

    def finish(self, request_id, frozen):
        try:
            result = self.retrieve(frozen['observation'])
            with self.lock:
                if request_id != self.generation:
                    return
            if not self.capture.still_selected(frozen):
                raise ValueError('Selection, stats or game focus changed; report suppressed')
            self.deliver(request_id, {'state': 'complete', 'frozen': frozen, 'result': result})
        except Exception as exc:
            self.deliver(request_id, {'state': 'rejected', 'reason': str(exc)})
