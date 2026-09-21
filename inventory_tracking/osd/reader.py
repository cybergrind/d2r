"""Host-only research reader adapter with build gating and process rediscovery."""

import json
import threading
import time
from dataclasses import asdict, replace
from tempfile import TemporaryDirectory

from ..capture_probe import capture_image
from ..common import LOG
from ..image_probe import inspect_images
from ..merc_heal import MercHealController
from ..merc_input import MercInput
from ..probe import inspect_game, select_game_process
from ..reports import publish
from ..unit_probe import inspect_units
from .state import State, from_research


SUPPORTED_SHA256 = '1e2ac459feb3f4bbfa818cdff49800480502beae9f90cfa4cba9e7e1f8bfa3b7'


class LiveReader:
    def __init__(self, directory, *, pid=None, interval=0.1, merc_heal=False, player_heal=False):
        self.directory = directory
        self.pid = pid
        self.interval = interval
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.last_reason = None
        self.controller = MercHealController() if merc_heal else None
        self.player_controller = MercHealController('player') if player_heal else None
        self.send = MercInput(directory.parent) if merc_heal or player_heal else None
        self.last_merc = None
        self.merc_potion_sent = None
        self.player_potion_sent = None
        self.state = State(time.monotonic(), reason='connecting')
        self.thread = threading.Thread(target=self.run, daemon=True, name='osd-reader')

    def latest(self):
        with self.lock:
            return self.state

    def send_potion(self, state, column, *, target='merc'):
        sent = self.send(state, column) if target == 'merc' else self.send(state, column, target=target)
        if sent:
            with self.lock:
                field = f'{target}_potion_sent'
                event = (time.monotonic(), column)
                setattr(self, field, event)
                self.state = replace(self.state, **{field: event})
        return sent

    def set_state(self, state):
        with self.lock:
            state = replace(state, merc_potion_sent=self.merc_potion_sent, player_potion_sent=self.player_potion_sent)
            self.state = state
        if state.reason != self.last_reason:
            LOG.info('Reader state: %s', state.reason or 'available')
            self.last_reason = state.reason
        if state.merc != self.last_merc:
            LOG.info('Mercenary sample: %s', state.merc)
            self.last_merc = state.merc
        publish(self.directory / 'state.json', asdict(state) | {'validated': False})

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
        LOG.info('Mercenary auto-heal: %s', 'enabled' if self.controller else 'disabled')
        LOG.info('Player auto-heal: %s', 'enabled' if self.player_controller else 'disabled')
        last_error = None
        while not self.stop_event.is_set():
            try:
                # One bounded image capture per attachment; temporary bytes are removed on disconnect.
                with TemporaryDirectory(prefix='capture-', dir=self.directory) as temporary:
                    from pathlib import Path

                    pid, images, capture = self.connect(Path(temporary))
                    last_error = None
                    while not self.stop_event.is_set():
                        result = inspect_units(pid, images, capture, self.directory, log_summary=False, merc=True)
                        if result['status'] != 'research':
                            raise ValueError('game changed; reconnecting')
                        snapshot = json.loads((self.directory / 'units.json').read_text())
                        state = from_research(snapshot)
                        self.set_state(state)
                        if state.reason:
                            LOG.debug(
                                'Rejected unit groups: %s',
                                {
                                    k: {
                                        'complete': v['complete'],
                                        'heads_stable': v['heads_stable'],
                                        'errors': v['errors'],
                                    }
                                    for k, v in snapshot['groups'].items()
                                },
                            )
                        if self.player_controller:
                            self.player_controller.step(
                                state,
                                time.monotonic(),
                                lambda sample, column: self.send_potion(sample, column, target='player'),
                            )
                            publish(
                                self.directory / 'player-heal.json',
                                {
                                    'enabled': True,
                                    'suspended': self.player_controller.suspended,
                                    'pending': self.player_controller.pending,
                                },
                            )
                        if self.controller:
                            self.controller.step(state, time.monotonic(), self.send_potion)
                            publish(
                                self.directory / 'merc-heal.json',
                                {
                                    'enabled': True,
                                    'suspended': self.controller.suspended,
                                    'pending': self.controller.pending,
                                    'last_attempt': (
                                        self.controller.last_attempt
                                        if self.controller.last_attempt != float('-inf')
                                        else None
                                    ),
                                    'gameplay_ready': state.gameplay_ready,
                                },
                            )
                        if self.stop_event.wait(self.interval):
                            break
            except Exception as exc:
                message = str(exc)
                self.set_state(State(time.monotonic(), reason='reader unavailable'))
                if message != last_error:
                    LOG.warning('OSD reader unavailable: %s', message)
                    last_error = message
                self.stop_event.wait(2)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=3)
