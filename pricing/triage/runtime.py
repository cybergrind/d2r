"""Process-local triage tables shared by automatic and on-demand assessments."""

from pricing.triage.adapters import from_drop
from pricing.triage.engine import Tables, assess


TABLES = Tables()


def warm(observation=None):
    TABLES.load()
    if observation is not None:
        retrieve(observation)


def retrieve(observation):
    return {'triage': assess(from_drop(observation), TABLES.load())}


def detail(observation, database, pinned=None):
    from inventory_tracking.appraisal.memory_backend import memory_evidence
    from inventory_tracking.appraisal.published_backend import retrieve_pinned

    result = retrieve_pinned(pinned, observation) if pinned is not None else memory_evidence(observation, database)
    candidate = retrieve(observation)['triage']
    return {**result, 'triage' if enabled(observation) else 'triage_candidate': candidate}


def enabled(observation):
    item = from_drop(observation)
    key = f'{item["category"]}/{item.get("family") or item.get("name")}'
    return key in TABLES.load()['rules'].get('enabled_types', [])


def guarded_retrieve(observation, database, pinned=None):
    result = fast_retrieve(observation)
    return result if result is not None else detail(observation, database, pinned)


def fast_retrieve(observation):
    """Return None for legacy routing; never build detail caches in a fast worker."""
    return retrieve(observation) if enabled(observation) else None


def shop_retrieve(observation):
    return retrieve(observation) if enabled(observation) else {}
