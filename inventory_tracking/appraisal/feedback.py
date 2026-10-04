"""Save explicit verdict disagreements, separately from expected-verdict labels."""

import json

from inventory_tracking.common import timestamp
from inventory_tracking.corpus.build import item_id
from pricing.knowledge.refresh import atomic_json


def flag(record, directory, source):
    if not record or record.get('state') != 'complete':
        return False
    result = record.get('result', {})
    observation = result.get('extraction')
    if not observation or not observation.get('item'):
        return False
    identifier = item_id(observation)
    path = directory / 'disagreements.json'
    rows = json.loads(path.read_text()) if path.exists() else {}
    if identifier in rows and rows[identifier].get('status') == 'pending':
        return False
    rows[identifier] = {
        'id': identifier,
        'status': 'pending',
        'reported_at': timestamp(),
        'source': source,
        'observation': observation,
        'triage': result.get('triage'),
    }
    directory.mkdir(parents=True, exist_ok=True)
    atomic_json(path, rows)
    return True
