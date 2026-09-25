"""Charged-skill availability independent of generated names and spell levels."""

from collections.abc import Mapping

from pricing.knowledge.assessment.domain.facts import FactStatus, StatKey


def charge_availability(facts, skill_id, minimum):
    observed = []
    uncertain = False
    for key, row in facts.stats.items():
        if not key.startswith('204:'):
            continue
        try:
            parameter = int(key.split(':')[1])
        except ValueError:
            uncertain = True
            continue
        if parameter >> 6 != skill_id:
            continue
        counts = row.get('charges', {})
        if not isinstance(counts, Mapping):
            uncertain = True
            continue
        remaining, maximum = counts.get('remaining'), counts.get('maximum')
        if (
            facts.stat(StatKey(204, parameter)).status != FactStatus.KNOWN
            or row.get('unit') != 'charges_remaining'
            or not 1 <= parameter & 63 <= 63
            or type(remaining) is not int
            or type(maximum) is not int
            or not 0 <= remaining <= maximum <= 255
            or maximum == 0
            or type(row.get('value')) is not int
            or row['value'] != remaining
        ):
            uncertain = True
            continue
        observed.append({'level': parameter & 63, 'remaining': remaining, 'maximum': maximum})
    if any(row['remaining'] >= minimum for row in observed):
        return 'true', observed
    if uncertain or (not observed and (not facts.capture_complete or facts.gaps)):
        return 'unknown', observed
    return 'false', observed
