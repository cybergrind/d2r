"""Build-gated live sampling, reconnect lifecycle, and diagnostic publication.

The unit table is found by a code signature (native/capture.py), and D2R.exe's code pages are
decrypted lazily, so in the menus the signature's page is often still encrypted and the scan finds
nothing: "unit table unavailable; enter a game with a character". The table's RVA is a constant of
the build, so a successful scan is remembered per executable sha256, the build gate's own
fingerprint and not the capture's hash, which is of the memory image (`unit-table.json` beside the
run directories) and a later attach in the lobby takes it from there (user, 2026-10-10: `make serve`
restarted in the lobby, then the macro request did nothing because nothing had attached).
"""

import json
import threading
import time
from dataclasses import asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory

from inventory_tracking.automation.controller import Automation
from inventory_tracking.common import LOG
from inventory_tracking.config import READER, RESOURCE_READER
from inventory_tracking.models import State
from inventory_tracking.native.capture_probe import capture_image
from inventory_tracking.native.image_probe import inspect_images
from inventory_tracking.native.layout import SUPPORTED_SHA256
from inventory_tracking.native.session import GameNotReady, inspect_game, select_game_process
from inventory_tracking.native.unit_probe import sample_units
from inventory_tracking.reports import publish
from inventory_tracking.tracking.consume import observe_consume
from inventory_tracking.tracking.shop_panel import observe_shop_panel
from inventory_tracking.tracking.show_items import observe_show_items
from inventory_tracking.tracking.state import from_research


UNIT_TABLE_CACHE = 'unit-table.json'  # {sha256: {'table_rva', 'signature_rva'}}, beside the run directories


class LiveReader:
    def __init__(
        self,
        directory,
        *,
        pid=None,
        config=READER,
        automation=None,
        observer=None,
        resource_config=RESOURCE_READER,
        table_cache: Path | None = None,
    ):
        self.resource_config = resource_config
        self.table_cache = Path(directory).parent / UNIT_TABLE_CACHE if table_cache is None else table_cache
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
        state = replace(state, events=self.automation.events, outcomes=self.automation.outcomes)
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
        build = game.get('executable_fingerprint', {}).get('sha256')
        if build != SUPPORTED_SHA256:
            raise ValueError('unsupported game build')
        images = inspect_images(pid, game)
        if images['status'] != 'candidate':
            # D2R.exe starting or exiting: the image is not (or no longer) mapped; retry.
            reason = images.get('error') or images['status']
            raise GameNotReady(f'game image unavailable ({reason})')
        capture = capture_image(pid, images, directory)
        if capture['status'] == 'stale':
            # The image changed or became unreadable mid-attach (game starting or exiting): retry.
            raise GameNotReady(f'game image changed during attach: {capture.get("error", "stale capture")}')
        if capture['status'] != 'captured':
            raise GameNotReady('unit table unavailable; enter a game with a character')
        if len({x['table_address'] for x in capture['unit_table_candidates']}) == 1:
            self.remember_table(build, capture)
        else:
            # In the menus the signature's code page is usually still encrypted (module docstring).
            cached = self.cached_table(build, capture)
            if cached is None:
                raise GameNotReady('unit table unavailable; enter a game with a character')
            capture['unit_table_candidates'] = [cached]
            LOG.info(
                'Unit table taken from %s: RVA %#x (no signature in the captured code)',
                self.table_cache,
                cached['table_rva'],
            )
        LOG.info('OSD attached to process %s', game['identity'])
        return pid, images, capture

    def _cache(self) -> dict:
        try:
            data = json.loads(self.table_cache.read_text())
        except OSError, ValueError:
            return {}
        return data if isinstance(data, dict) else {}

    def remember_table(self, build: str, capture) -> None:
        """Keep the scanned table's RVA for this build, for attaches in the menus."""
        [found] = {x['table_rva']: x for x in capture['unit_table_candidates']}.values()
        entry = {'table_rva': found['table_rva'], 'signature_rva': found['signature_address'] - capture['base']}
        cache = self._cache()
        if cache.get(build) != entry:
            cache[build] = entry
            try:
                self.table_cache.parent.mkdir(parents=True, exist_ok=True)
                self.table_cache.write_text(json.dumps(cache, indent=1, sort_keys=True))
            except OSError as exc:
                LOG.info('Unit table not remembered in %s: %s', self.table_cache, exc)

    def cached_table(self, build: str, capture) -> dict | None:
        """The remembered table of this build at this process's base, or None."""
        entry = self._cache().get(build)
        if not entry or 'base' not in capture:
            return None
        return {
            'signature_address': capture['base'] + entry['signature_rva'],
            'table_rva': entry['table_rva'],
            'table_address': capture['base'] + entry['table_rva'],
        }

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
                        if state.session is not None:
                            state = replace(
                                state,
                                show_items=observe_show_items(pid, images),
                                consume=observe_consume(pid, images, snapshot, state.session.player_id),
                                shop=observe_shop_panel(pid, images, snapshot),
                            )
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
