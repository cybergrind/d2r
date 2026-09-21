"""Cross-instance serialization and durable potion state (one ledger per host)."""

import fcntl
import json
import math
from contextlib import contextmanager
from pathlib import Path

from .models import Actor, PotionType
from .reports import publish


def validate_ledger(data):
    """Reject malformed persisted policy before it can weaken an input guard."""

    def timestamp(value):
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError('Invalid potion ledger timestamp')

    if not isinstance(data['actors'], dict) or not isinstance(data['cooldowns'], dict):
        raise ValueError('Invalid potion ledger maps')
    if data['legacy_sent_at'] is not None:
        timestamp(data['legacy_sent_at'])
    valid_keys = {f'{actor}:{potion}' for actor in Actor for potion in PotionType}
    for key, value in data['cooldowns'].items():
        if key not in valid_keys:
            raise ValueError('Invalid potion cooldown key')
        timestamp(value)
    for actor, record in data['actors'].items():
        if actor not in Actor or not isinstance(record, dict):
            raise ValueError('Invalid potion actor record')
        if not isinstance(record['session'], list) or len(record['session']) != 4:
            raise ValueError('Invalid potion session')
        if type(record['suspended']) is not bool:
            raise ValueError('Invalid potion suspension')
        pending = record['pending']
        if pending is not None:
            if not isinstance(pending, dict) or type(pending['item_id']) is not int:
                raise ValueError('Invalid potion reservation')
            timestamp(pending['sent_at'])
    delivery = data['last_delivery']
    if delivery is not None:
        if not isinstance(delivery, dict) or not isinstance(delivery['session'], list) or len(delivery['session']) != 3:
            raise ValueError('Invalid potion delivery marker')
        timestamp(delivery['at'])


class LedgerTransaction:
    def __init__(self, path, data):
        self.path = path
        self.data = data

    def save(self):
        publish(self.path, self.data)


class PotionLedger:
    def __init__(self, directory, *, boot_id=None):
        # Keep the old path: existing cooldowns must survive this migration.
        self.lock_path = directory / 'merc-input.lock'
        self.path = directory / 'potions.json'
        self.boot_id = boot_id or Path('/proc/sys/kernel/random/boot_id').read_text().strip()

    @contextmanager
    def transaction(self):
        with self.lock_path.open('a+') as file:
            fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            file.seek(0)
            contents = self.path.read_text() if self.path.exists() else file.read()
            data = json.loads(contents) if contents else {}
            if not isinstance(data, dict):
                raise ValueError('Potion ledger must be a JSON object')
            if data.get('boot') != self.boot_id:
                data = {'boot': self.boot_id}
            version = data.get('version')
            if version is None:
                data = {
                    'version': 1,
                    'boot': self.boot_id,
                    'legacy_sent_at': data.get('sent_at'),
                    'cooldowns': {},
                    'actors': {},
                    'last_delivery': None,
                }
            elif version != 1:
                raise ValueError('Unsupported potion ledger version')
            validate_ledger(data)
            transaction = LedgerTransaction(self.path, data)
            # Exceptions propagate and skip save on purpose: a failed step must not publish
            # partial state, and the lock file closes with the enclosing `with`.
            yield transaction  # ruff: ignore[fallible-context-manager]
            transaction.save()
