"""Resolve reviewed annotation targets to actual decoded native stat rows.

charge:<skill id> selects usable charged-skill rows across spell levels. It is not
an alias for a scalar bonus and never selects exhausted or malformed charge rows.
"""

from pricing.knowledge.assessment.roles.charges import charge_availability
from pricing.knowledge.assessment.roles.predicates import validate


def charge_target(key):
    if not isinstance(key, str) or not key.startswith('charge:'):
        return None
    try:
        skill = int(key.removeprefix('charge:'))
    except ValueError as error:
        raise ValueError('Invalid charged-skill target') from error
    if key != f'charge:{skill}' or not 0 <= skill <= 4095:
        raise ValueError('Invalid charged-skill target')
    return skill


def validate_target(key):
    if charge_target(key) is None:
        validate({'op': 'stat_at_least', 'key': key, 'value': 0})


def target_keys(key, facts):
    skill = charge_target(key)
    if skill is None:
        return (key,)
    status, rows = charge_availability(facts, skill, 1)
    if status != 'true':
        return ()
    return tuple(f'204:{skill * 64 + row["level"]}' for row in rows if row['remaining'] > 0)
