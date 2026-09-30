"""Validate explicitly reviewed mercenary equipment alternatives without merging contexts."""

import re

from inventory_tracking.items.stat_constants import CLASS_NAMES
from pricing.knowledge.assessment.maintenance.context_values import context_values
from pricing.knowledge.assessment.maintenance.source_matching import requires_eq


MERCENARY_SLOTS = frozenset({'Weapon', 'Body Armor', 'Helmet'})


def declared_types(row):
    values = row.get('mercenary_types')
    if (
        'mercenary_type' in row
        or not isinstance(values, list)
        or not values
        or any(not isinstance(value, str) or not value.strip() for value in values)
        or len(set(values)) != len(values)
    ):
        raise ValueError('Invalid source-context mercenary types')
    return frozenset(values)


def _mentioned(value, text):
    return re.search(r'(?<!\w)' + re.escape(value) + r'(?!\w)', text) is not None


def branch_matches(branch, role, quote):
    values = declared_types(branch)
    actual = context_values(role.get('must', {}), 'mercenary_type')
    if 'role_mercenary_types' in branch:
        declared_role = declared_types({'mercenary_types': branch['role_mercenary_types']})
        supported = declared_role == actual and values <= declared_role
    else:
        supported = values == actual
    return supported and all(_mentioned(value, quote) for value in values)


def validate_branches(review, remaining, quote):
    required = declared_types(review)
    covered = frozenset().union(*(declared_types(branch) for branch in review['branches']))
    if covered - required or any(not _mentioned(value, quote) for value in required):
        raise ValueError('Unsupported source-context mercenary alternatives')
    missing = required - covered
    if missing and (not remaining or any(not _mentioned(value, ' '.join(remaining)) for value in missing)):
        raise ValueError('Unreviewed source-context mercenary branches must remain explicit')


def corrected_prose_matches(branch, role, occurrence, quote):
    """Narrow explicit instruction grammar for a misattributed Might weapon mention."""
    klass = branch.get('player_class')
    return (
        klass == occurrence.get('class')
        and klass in CLASS_NAMES
        and role.get('slot') == 'Weapon'
        and branch.get('mercenary_type') == 'Act 2 Might'
        and isinstance(branch.get('configuration_review'), str)
        and bool(branch['configuration_review'].strip())
        and requires_eq(role.get('must', {}), 'context_eq', 'player_class', klass)
        and requires_eq(role.get('must', {}), 'context_eq', 'mercenary_type', 'Act 2 Might')
        and _mentioned('Desert Mercenary with Might Aura', quote)
        and _mentioned('Equip him with ' + occurrence['original_label'], quote)
    )


def support_prose_matches(branch, role, occurrence, quote):
    """Reviewed physical-support weapon alternatives with an explicit wearer clause."""
    types = {"The Reaper's Toll": 'Act 2 Might', 'Lawbringer': 'Act 5 Frenzy'}
    name = occurrence.get('name')
    if name not in types:
        return False
    klass = branch.get('player_class')
    mercenary = types[name]
    # A shared sentence joins these alternatives to the mercenary's Decrepify.
    # Neither an isolated name nor nearby unrelated mercenary prose is sufficient.
    equipment = "The Reaper's Toll or Lawbringers"
    explicit = (
        'Mercenary to apply Decrepify from his ' + equipment in quote
        or 'Use a Mercenary with ' + equipment + ' for Decrepify' in quote
    )
    return (
        explicit
        and klass in CLASS_NAMES
        and klass == occurrence.get('class')
        and role.get('slot') == 'Weapon'
        and branch.get('mercenary_type') == mercenary
        and isinstance(branch.get('configuration_review'), str)
        and bool(branch['configuration_review'].strip())
        and requires_eq(role.get('must', {}), 'context_eq', 'player_class', klass)
        and requires_eq(role.get('must', {}), 'context_eq', 'mercenary_type', mercenary)
    )
