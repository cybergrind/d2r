"""Plain named caster gear retains its original variant conditions."""

import json
from pathlib import Path

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence


ROOT = Path(__file__).resolve().parents[5]
THRESHOLDS = {
    'nova-sorceress-guide-3-magefist': (None, None),
    'poison-nova-necromancer-2-trang-claws': (125, None),
    'meteor-standard-arachnid': (63, 60),
    'meteor-sorceress-3-magefist': (105, 86),
    'meteor-sorceress-1-magefist': (63, 60),
    'fissure-druid-1-magefist': (99, None),
    'enchant-sorceress-1-magefist': (None, None),
    'wake-of-fire-assassin-1-magefist': (102, None),
    'lightning-sentry-assassin-1-magefist': (65, None),
    'fissure-druid-2-magefist': (None, None),
    'nova-sorceress-guide-1-magefist': (105, None),
    'nova-sorceress-guide-2-magefist': (None, None),
    'blizzard-standard-arachnid': (105, None),
    'fist-of-the-heavens-paladin-3-magefist': (75, 48),
    'fire-blast-assassin-1-magefist': (102, None),
    'lightning-standard-arachnid': (117, None),
    'fist-of-the-heavens-paladin-2-magefist': (125, None),
    'summoner-necromancer-guide-1-trang-claws': (125, None),
    'poison-nova-necromancer-1-trang-claws': (125, None),
    'meteor-sorceress-4-magefist': (105, 86),
    'poison-nova-necromancer-0-trang-claws': (75, None),
    'fire-warlock-guide-1-magefist': (None, None),
    'summoner-necromancer-guide-2-trang-claws': (75, None),
}


def test_caster_gear_source_reviews_preserve_fcr_recovery_and_upgrade_predicates():
    def read(path):
        return json.loads((ROOT / path).read_text())

    rows = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['profile_id'] in THRESHOLDS
    ]
    assert len(rows) == len(THRESHOLDS) == 23
    profiles = read('pricing/data/appraisal-build-profiles.json')['profiles']
    occurrences = read('pricing/data/appraisal-guide-inventory.json')['occurrences']
    result = compile_table_equivalence(
        {'schema_version': 1, 'rows': rows},
        occurrences,
        profiles,
        read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'],
        ROOT,
    )
    assert {r['profile_id'] for r in result} == set(THRESHOLDS)
    assert all(r['state'] == 'reviewed' for r in result)
    by_id = {r['id']: r for r in profiles}
    by_occurrence = {r['id']: r for r in occurrences}
    for review in rows:
        role = by_id[review['profile_id']]
        occurrence = by_occurrence[review['occurrence_id']]
        assert occurrence['original_label'] == review['canonical_name']
        assert review['required_predicates'] == role['must']['all']
        predicates = review['required_predicates']
        assert {'op': 'context_eq', 'field': 'player_class', 'value': occurrence['class']} in predicates
        for field, threshold in zip(('player_total_fcr', 'player_total_fhr'), THRESHOLDS[role['id']], strict=True):
            actual = [p for p in predicates if p.get('field') == field]
            assert actual == (
                [] if threshold is None else [{'op': 'context_at_least', 'field': field, 'value': threshold}]
            )
        if review['canonical_name'] == 'Magefist':
            # Native and upgraded glove bases remain alternatives, not three requirements.
            alternatives = next(p['any'] for p in predicates if 'any' in p)
            assert len(alternatives) == 3
            assert all(p['op'] == 'fact_eq' and p['field'] == 'base_code' for p in alternatives)
