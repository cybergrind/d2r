"""Reviewed supplementary named-item leveling uses and explicit review dispositions."""

import hashlib
import json
from functools import lru_cache

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.domain.facts import thaw
from pricing.knowledge.assessment.mechanics.equipment import assess_requirements, named_requirements
from pricing.knowledge.assessment.policies.named_baselines import ROOT


RULES = ROOT / 'pricing/knowledge/assessment/rules/named_leveling_reviews.json'


@lru_cache(maxsize=2)
def _rows(raw, inputs):
    document = json.loads(raw)
    if document.get('schema_version') != 1:
        raise ValueError('Unsupported named leveling schema')
    for path, content in inputs:
        if hashlib.sha256(content).hexdigest() != document['inputs'][path]:
            raise ValueError('Named leveling evidence changed')
    rows = {}
    for row in document['rows']:
        key = row['quality'], row['name']
        if key in rows or row['status'] not in (
            'recommendation',
            'conditional_combination',
            'no_specific_recommendation',
        ):
            raise ValueError('Invalid named leveling review')
        if not row.get('reason') or not row.get('native_table_ids'):
            raise ValueError('Unreviewed named leveling identity')
        if 'recommendation' in row and row['recommendation']['tier'] not in ('high', 'med', 'low'):
            raise ValueError('Invalid leveling recommendation tier')
        rows[key] = row
    return rows


def reviews():
    raw = read_artifact(RULES)
    document = json.loads(raw)
    inputs = tuple((path, read_artifact(ROOT / path)) for path in document['inputs'])
    return _rows(raw, inputs)


def supplemental_uses(facts, definition, *, loadout=None):
    try:
        row = reviews().get((facts.rarity, facts.name))
    except OSError, ValueError, KeyError, TypeError:
        return []
    if row is None or 'recommendation' not in row or definition['table_id'] not in row['native_table_ids']:
        return []
    if facts.rarity == 'set' and facts.ethereal is True:
        return []
    use = row['recommendation']
    conditions = list(use.get('conditions', []))
    requirements = named_requirements(facts, definition, thaw(row['requirements']))
    if not requirements:
        conditions.append('Equip requirements for this variant need verification before leveling use.')
    return [
        {
            **use,
            'status': 'conditional' if conditions else 'recommended',
            'conditions': conditions,
            'required_level': requirements.get('level'),
            'requirements': requirements,
            'requirements_fit': assess_requirements(requirements, use['side'], loadout),
            'stage': 'leveling',
            'source': {
                'id': str(RULES.relative_to(ROOT)),
                'locator': f'{facts.rarity}:{facts.name}',
                'date': row['reviewed_at'],
                'review': row['reason'],
            },
        }
    ]
