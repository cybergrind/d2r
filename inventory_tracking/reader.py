"""Build-gated live sampling, reconnect lifecycle, and diagnostic publication."""

import threading
import time
from dataclasses import asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory

from .automation import Automation
from .capture_probe import capture_image
from .common import LOG
from .config import READER, RESOURCE_READER
from .image_probe import inspect_images
from .layout import SUPPORTED_SHA256
from .models import State
from .probe import inspect_game, select_game_process
from .reports import publish
from .state import from_research
from .unit_probe import sample_units


class LiveReader:
    def __init__(
        self, directory, *, pid=None, config=READER, automation=None, observer=None, resource_config=RESOURCE_READER
    ):
        self.resource_config = resource_config
        self.observer = observer
        self.observer_error = None
        self.directory = directory
        self.pid = pid
        self.config = config
        self.automation = automation if automation is not None else Automation([])
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.last_reason = None
        self.last_merc = None
        self.state = State(sampled_at=time.monotonic(), reason='connecting')
        self.thread = threading.Thread(target=self.run, daemon=True, name='game-reader')

    def latest(self):
        with self.lock:
            return self.state

    def set_state(self, state):
        state = replace(state, events=self.automation.events)
        with self.lock:
            self.state = state
        if self.observer is not None:
            try:
                self.observer(state)
                self.observer_error = None
            except Exception as exc:
                if str(exc) != self.observer_error:
                    LOG.exception('State observer failed')
                self.observer_error = str(exc)
        if state.reason != self.last_reason:
            LOG.info('Reader state: %s', state.reason or 'available')
            self.last_reason = state.reason
        if state.merc != self.last_merc:
            LOG.info('Mercenary sample: %s', state.merc)
            self.last_merc = state.merc
        publish(self.directory / 'state.json', asdict(state))

    def connect(self, directory):
        pid = select_game_process(self.pid)
        game = inspect_game(pid)
        if not game.get('memory_access'):
            raise ValueError('memory unavailable')
        if game.get('executable_fingerprint', {}).get('sha256') != SUPPORTED_SHA256:
            raise ValueError('unsupported game build')
        images = inspect_images(pid, game)
        if images['status'] != 'candidate':
            raise ValueError('game image unavailable')
        capture = capture_image(pid, images, directory)
        if capture['status'] != 'captured' or len({x['table_address'] for x in capture['unit_table_candidates']}) != 1:
            raise ValueError('unit table unavailable')
        LOG.info('OSD attached to process %s', game['identity'])
        return pid, images, capture

    def run(self):
        last_error = None
        while not self.stop_event.is_set():
            try:
                with TemporaryDirectory(prefix='capture-', dir=self.directory) as temporary:
                    pid, images, capture = self.connect(Path(temporary))
                    last_error = None
                    while not self.stop_event.is_set():
                        snapshot = sample_units(
                            pid,
                            images,
                            capture,
                            merc=True,
                            **({'resources': True} if self.resource_config.enabled else {}),
                        )
                        publish(self.directory / 'units.json', snapshot)
                        if snapshot['status'] != 'research':
                            raise ValueError('game changed; reconnecting')
                        state = from_research(snapshot, resource_config=self.resource_config)
                        results = self.automation.step(state)
                        for actor, result in results.items():
                            publish(self.directory / f'{actor}-heal.json', asdict(result))
                        self.set_state(state)
                        if self.stop_event.wait(self.config.interval):
                            break
            except Exception as exc:
                message = str(exc)
                self.set_state(State(sampled_at=time.monotonic(), reason='reader unavailable'))
                if message != last_error:
                    LOG.warning('Reader unavailable: %s', message)
                    last_error = message
                self.stop_event.wait(self.config.reconnect_delay)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=self.config.shutdown_timeout)
