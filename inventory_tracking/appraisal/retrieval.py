"""One observation's KB retrieval: the detail engine (published or in-memory KB) plus the triage verdict.

Runs in a retrieval process (`retrieval_process.py`); its timing log lines name these functions.
"""

from inventory_tracking.appraisal.memory_backend import memory_evidence
from inventory_tracking.appraisal.published_backend import retrieve_pinned
from pricing.api import fast_triage, triage, triage_enabled


def detail(observation, database, pinned=None):
    result = retrieve_pinned(pinned, observation) if pinned is not None else memory_evidence(observation, database)
    candidate = triage(observation)['triage']
    return {**result, 'triage' if triage_enabled(observation) else 'triage_candidate': candidate}


def guarded_retrieve(observation, database, pinned=None):
    """The fast triage verdict where its item type is enabled, else the detail engine."""
    result = fast_triage(observation)
    return result if result is not None else detail(observation, database, pinned)
