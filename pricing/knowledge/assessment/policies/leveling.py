"""Leveling use from reviewed recommendations, independent of trade pricing."""

import json
from functools import lru_cache
from pathlib import Path

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.domain.facts import freeze, thaw
from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
from pricing.knowledge.assessment.mechanics.equipment import assess_requirements
from pricing.knowledge.assessment.policies.generic_leveling import assess_generic_leveling


DATA = Path(__file__).resolve().parents[3] / 'data'
# Existing reviewed recommendation ordering: 1 strongest, 2/3 ordinary utility,
# 5 farming-first. This qualitative leveling policy does not assign trade tiers.
PRIORITY_TIERS = {1: 'high', 2: 'med', 3: 'med', 5: 'low'}


@lru_cache(maxsize=2)
def _load(recommendation_bytes, fact_bytes):
    recommendations = json.loads(recommendation_bytes)
    facts = json.loads(fact_bytes)
    if recommendations.get('schema_version') != 1 or facts.get('schema_version') != 1:
        raise ValueError('Unsupported leveling artifact schema')
    identities = {r['item_id']: r for r in facts['rows']}
    index = {}
    for row in recommendations['rows']:
        identity = identities.get(row.get('item_id'))
        if not identity or row.get('intent') != 'recommend' or row.get('purpose') != 'leveling':
            continue
        if not row.get('review') or row.get('evidence_strength') not in ('explicit', 'reviewed_inference'):
            continue
        if row.get('priority') not in PRIORITY_TIERS or row['name'] != identity['name']:
            continue
        index.setdefault((identity['quality'], identity['name']), []).append((row, identity))
    return freeze(index)


def assess_leveling(facts, *, loadout=None):
    generic = assess_generic_leveling(facts, loadout=loadout)
    if facts.rarity in ('magic', 'rare', 'crafted'):
        return generic
    if facts.identified is not True or facts.rarity not in ('unique', 'set'):
        return generic
    try:
        definition, _ = resolve_named_definition(facts)
        if definition is None:
            return []
        index = _load(
            read_artifact(DATA / 'appraisal-recommendations.json'), read_artifact(DATA / 'appraisal-item-facts.json')
        )
    except OSError, ValueError, KeyError, TypeError:
        return []  # No reviewed use claimed; never infer a "none" tier from missing data.
    uses = list(generic)
    seen = set()
    for source, identity in index.get((facts.rarity, facts.name), ()):
        if facts.item_type != identity.get('item_type') or (facts.rarity == 'set' and facts.ethereal is True):
            continue
        conditions = thaw(source.get('conditions', ()))
        key = (
            source['side'],
            tuple(source['archetypes']),
            tuple(source['classes']),
            source['reason'],
            tuple(conditions),
        )
        if key in seen:
            continue
        seen.add(key)
        original = facts.base_code == identity.get('base_code') and facts.ethereal is False and facts.sockets == 0
        requirements = thaw(identity.get('requirements', {})) if original and identity.get('requirements_known') else {}
        if not requirements:
            conditions.append('Equip requirements for this variant need verification before leveling use.')
        uses.append(
            {
                'tier': PRIORITY_TIERS[source['priority']],
                'status': 'conditional' if conditions else 'recommended',
                'side': source['side'],
                'classes': thaw(source['classes']),
                'archetypes': thaw(source['archetypes']),
                'reason': source['reason'],
                'conditions': conditions,
                'required_level': requirements.get('level'),
                'requirements': requirements,
                'requirements_fit': assess_requirements(requirements, source['side'], loadout),
                'stage': source['stage'],
                'source': {
                    'id': source['source_id'],
                    'locator': source['source_locator'],
                    'date': source.get('source_date'),
                    'review': source['review'],
                },
            }
        )
    return uses
