"""Process-local triage tables shared by automatic and on-demand assessments.

The detail-engine fallback around them is host glue: `inventory_tracking.appraisal.retrieval`.
"""

from pricing.triage.adapters import from_drop
from pricing.triage.engine import Tables, assess


TABLES = Tables()


def warm(observation=None):
    TABLES.load()
    if observation is not None:
        retrieve(observation)


def retrieve(observation):
    return {'triage': assess(from_drop(observation), TABLES.load())}


def enabled(observation):
    item = from_drop(observation)
    key = f'{item["category"]}/{item.get("family") or item.get("name")}'
    return key in TABLES.load()['rules'].get('enabled_types', [])


def fast_retrieve(observation):
    """Return None for legacy routing; never build detail caches in a fast worker."""
    return retrieve(observation) if enabled(observation) else None


def shop_retrieve(observation):
    return retrieve(observation) if enabled(observation) else {}
