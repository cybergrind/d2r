"""Freeze requests before asynchronous evidence retrieval; publish newest only."""

import math
import threading
import time
from contextlib import nullcontext
from contextvars import copy_context

from inventory_tracking.appraisal.cache import ResultCache, item_key


class AppraisalWorker:
    def __init__(
        self,
        capture,
        retrieve,
        publish,
        executor,
        *,
        display=None,
        display_seconds=30,
        cache_seconds=300,
        clock=time.monotonic,
        cache_context=lambda: None,
        request_scope=nullcontext,
    ):
        self.capture, self.retrieve, self.publish, self.executor = capture, retrieve, publish, executor
        self.lock = threading.Lock()
        self.generation = 0
        self.last_request = -math.inf
        self.future = None
        self.display = display
        self.display_seconds, self.clock = display_seconds, clock
        self.cache = ResultCache(cache_seconds)
        self.cache_context = cache_context
        self.request_scope = request_scope
        self.visible = None
        self.visible_context = None
        self.expires = 0.0
        self.capture_lock = threading.Lock()

    def request(self, requested_at, now):
        if not math.isfinite(requested_at) or not 0 <= now - requested_at <= 1 or now - self.last_request < 0.35:
            return False
        with self.lock:
            self.last_request = now
            self.generation += 1
            request_id = self.generation
            if self.future:
                self.future.cancel()
            self.hide()
            self.publish({'request_id': request_id, 'state': 'pending'})
        try:
            with self.request_scope():
                with self.capture_lock:
                    frozen = self.capture.freeze()
                key = item_key(frozen, self.cache_context())
                context = copy_context()
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
        with self.lock:
            cached = self.cache.get(key, self.clock())
        if cached is not None:
            if 'extraction' in cached:
                cached['extraction'] = frozen['observation']
            context.run(self.complete, request_id, frozen, cached, cache_hit=True)
        else:
            self.future = self.executor.submit(context.run, self.finish, request_id, frozen, key)
        return True

    def deliver(self, request_id, result):
        with self.lock:
            if request_id != self.generation:
                return False
            record = {'request_id': request_id, **result}
            self.publish(record)
            if result['state'] == 'complete' and self.display:
                self.visible = record
                self.visible_context = copy_context()
                self.expires = self.clock() + self.display_seconds
                self.display(record)
            return True

    def hide(self):
        self.visible = None
        self.visible_context = None
        if self.display:
            self.display(None)

    def tick(self):
        """Fail closed on hover/focus loss; never re-arm without a new hotkey."""
        with self.lock:
            record = self.visible
            context = self.visible_context
        if record is None:
            return
        try:
            with self.capture_lock:
                selected = self.clock() < self.expires and context.copy().run(
                    self.capture.still_selected, record['frozen']
                )
        except Exception:
            selected = False
        with self.lock:
            if self.visible is not record:
                return
            if not selected or self.clock() >= self.expires:
                self.hide()
            elif self.display:
                self.display(record)

    def complete(self, request_id, frozen, result, *, cache_hit=False):
        try:
            with self.lock:
                if request_id != self.generation:
                    return
            with self.capture_lock:
                selected = self.capture.still_selected(frozen)
            if not selected:
                raise ValueError('Selection, stats or game focus changed; report suppressed')
            self.deliver(
                request_id,
                {
                    'state': 'complete',
                    'frozen': frozen,
                    'result': result,
                    'cache_hit': cache_hit,
                },
            )
        except Exception as exc:
            self.deliver(request_id, {'state': 'rejected', 'reason': str(exc)})

    def finish(self, request_id, frozen, key):
        try:
            result = self.retrieve(frozen['observation'])
            with self.lock:
                self.cache.put(key, result, self.clock())
            self.complete(request_id, frozen, result)
        except Exception as exc:
            self.deliver(request_id, {'state': 'rejected', 'reason': str(exc)})
