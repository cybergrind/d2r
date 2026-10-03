"""Unpublished-KB retrieval for a memory snapshot (the service's fallback without a publication store)."""

from pricing.knowledge.pipeline import retrieve_draft


def memory_evidence(observation, database):
    result = retrieve_draft(observation, database)
    result['decision'].update(
        reason='Memory snapshot with limited stat decoding; local evidence requires review.',
        next_step='Review observed stats and unresolved fields against the local appraisal evidence.',
    )
    return result
