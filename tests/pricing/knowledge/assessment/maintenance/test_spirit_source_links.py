"""Spirit components retain total breakpoints and named companion requirements."""

import json
from pathlib import Path

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence


ROOT = Path(__file__).resolve().parents[5]
EXPECTED = {
    'holy-bolt-starter-spirit-shield': ('Paladin', 'pa1', None, None, ()),
    'hammer-starter-spirit-shield': ('Paladin', 'pa1', None, None, ()),
    'foh-starter-spirit-shield': ('Paladin', 'pa1', None, None, ()),
    'hammer-starter-spirit-sword': ('Paladin', 'crs', None, None, ()),
    'blizzard-starter-spirit-sword': ('Sorceress', 'crs', None, None, ()),
    'fissure-starter-spirit-sword': ('Druid', 'crs', None, None, ()),
    'lightning-starter-spirit-sword': ('Sorceress', 'crs', 117, None, ()),
    'lightning-starter-spirit-shield': ('Sorceress', 'uit', 117, None, ()),
    'meteor-standard-spirit-shield': ('Sorceress', 'uit', 63, 60, ()),
    'hammer-mf-spirit-shield': ('Paladin', 'pab', 125, None, ('Void', 'Sling', 'Arachnid Mesh')),
    'hammer-standard-spirit-shield': ('Paladin', 'pab', 125, None, ('Sling', "Hellwarden's Will")),
    'meteor-mf-spirit-shield': (
        'Sorceress',
        'uit',
        105,
        60,
        (
            'The Oculus',
            "Tal Rasha's Guardianship",
            "Tal Rasha's Fine-Spun Cloth",
            "Tal Rasha's Adjudication",
        ),
    ),
    'meteor-set-spirit-shield': (
        'Sorceress',
        'uit',
        105,
        86,
        (
            "Tal Rasha's Lidless Eye",
            "Tal Rasha's Horadric Crest",
            "Tal Rasha's Guardianship",
            "Tal Rasha's Fine-Spun Cloth",
            "Tal Rasha's Adjudication",
        ),
    ),
    'blizzard-set-spirit-shield': (
        'Sorceress',
        'uit',
        105,
        86,
        (
            "Tal Rasha's Lidless Eye",
            "Tal Rasha's Horadric Crest",
            "Tal Rasha's Guardianship",
            "Tal Rasha's Fine-Spun Cloth",
            "Tal Rasha's Adjudication",
        ),
    ),
}


def test_spirit_sources_preserve_exact_base_and_full_setup_dependencies():
    def read(path):
        return json.loads((ROOT / path).read_text())

    rows = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['profile_id'] in EXPECTED
    ]
    assert len(rows) == len(EXPECTED) == 14
    result = compile_table_equivalence(
        {'schema_version': 1, 'rows': rows},
        read('pricing/data/appraisal-guide-inventory.json')['occurrences'],
        read('pricing/data/appraisal-build-profiles.json')['profiles'],
        read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'],
        ROOT,
    )
    assert {r['profile_id'] for r in result} == set(EXPECTED)
    assert all(r['state'] == 'reviewed' for r in result)
    for row in rows:
        klass, base, fcr, fhr, companions = EXPECTED[row['profile_id']]
        assert row['required_predicates'] == [
            {'op': 'context_eq', 'field': 'player_class', 'value': klass},
            *[
                {'op': 'fact_eq', 'field': field, 'value': value}
                for field, value in (
                    ('identified', True),
                    ('base_code', base),
                    ('runeword', 'Spirit'),
                    ('sockets', 4),
                    ('socket_contents', 'filled'),
                )
            ],
        ]
        dependencies = row['required_dependencies']
        for field, value in (('player_total_fcr', fcr), ('player_total_fhr', fhr)):
            assert [d for d in dependencies if d.get('field') == field] == (
                [] if value is None else [{'op': 'context_at_least', 'field': field, 'value': value}]
            )
        assert [d['value'] for d in dependencies if d.get('field') == 'player_items'] == list(companions)
        alternatives = [d for d in dependencies if 'any' in d]
        assert alternatives == (
            [
                {
                    'any': [
                        {'op': 'context_contains', 'field': 'player_items', 'value': 'The Oculus'},
                        {'op': 'context_contains', 'field': 'player_items', 'value': "Eschuta's Temper"},
                    ]
                }
            ]
            if row['profile_id'] == 'meteor-standard-spirit-shield'
            else []
        )


def test_narrative_spirit_label_quote_must_be_a_verified_source_quote():
    import copy

    import pytest

    from pricing.knowledge.assessment.maintenance.structured_named_variants import validate_link
    from pricing.knowledge.assessment.maintenance.table_equivalence import _read

    def read(path):
        return json.loads((ROOT / path).read_text())

    row = next(
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['profile_id'] == 'blizzard-set-spirit-shield'
    )
    role = next(
        r for r in read('pricing/data/appraisal-build-profiles.json')['profiles'] if r['id'] == row['profile_id']
    )
    occurrence = next(
        r for r in read('pricing/data/appraisal-guide-inventory.json')['occurrences'] if r['id'] == row['occurrence_id']
    )
    uses = read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses']
    assert row['source_label_quote'] == (
        "Obtain an additional 6% FHR from Charms, along with the full Tal's Set and Spirit Monarch. "
        'Use Cold Rupture instead of Chilling Grand Charm of Vita to enable farming of any monster.'
    )
    validate_link(row, occurrence, role, uses, ROOT, lambda pin: json.loads(_read(ROOT, pin)))
    for invalid in ('Spirit Monarch invented quotation', role['source']['quotes'][2], None):
        changed = copy.deepcopy(row)
        changed['source_label_quote'] = invalid
        with pytest.raises(ValueError, match='source label or context changed'):
            validate_link(changed, occurrence, role, uses, ROOT, lambda pin: json.loads(_read(ROOT, pin)))
