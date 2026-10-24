"""Affix effects whose native stats have no one-to-one market property.

The capture adapter projects every stat with a verified market identity. These stats need item context
(flat damage mirrored on three stats, charges, procs, per-level rates, cold and poison durations).
The detail engine (`handlers/exact.py`) and triage (`pricing/triage/adapters.py from_drop`) both read
them through this one list, so the two paths always see the same market properties (2026-10-22: triage
had lost the flat damage, and a 15-max Jewel of Carnage was sold as vendor).
"""

from pricing.knowledge.assessment.mechanics.affixed_charges import affixed_charge_properties
from pricing.knowledge.assessment.mechanics.affixed_cold import affixed_cold_properties
from pricing.knowledge.assessment.mechanics.affixed_per_level import affixed_per_level_properties
from pricing.knowledge.assessment.mechanics.affixed_physical import affixed_physical_properties
from pricing.knowledge.assessment.mechanics.affixed_poison import affixed_poison_properties
from pricing.knowledge.assessment.mechanics.affixed_triggers import affixed_trigger_properties


PROJECTORS = (
    affixed_charge_properties,
    affixed_trigger_properties,
    affixed_per_level_properties,
    affixed_cold_properties,
    affixed_poison_properties,
    affixed_physical_properties,
)


def affix_effect_properties(facts):
    """(market properties, consumed native stat keys, gaps) of an affixed item's context-dependent effects."""
    properties, consumed, gaps = {}, set(), []
    for project in PROJECTORS:
        values, keys, errors = project(facts)
        for key, value in values.items():
            if key in properties and properties[key] != value:
                gaps.append(f'Affix effects conflict on market property {key}.')
            properties[key] = value
        consumed |= keys
        gaps.extend(errors)
    return properties, consumed, gaps
