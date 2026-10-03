"""Element and trigger identity must survive trade qualification, not just pricing."""

import json
from copy import deepcopy
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.policies import named_tiers
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.test_facet_catalog_comparisons import VARIANTS, capture


PROPERTIES = {329: '750', 333: '735', 330: '743', 334: '736', 331: '747', 335: '609', 332: '783', 336: '723'}


def document():
    policy = next(p for p in json.loads(named_tiers.RULES.read_bytes())['policies'] if p['name'] == 'Rainbow Facet')
    for variant, spec in zip(policy['variant_rules'], VARIANTS, strict=True):
        table, catalog, label, _, _, _, damage, pierce, _, _trigger = spec
        rows = []
        for perfect in (False, True):
            for seller in range(3):
                rows.append(
                    {
                        'id': f'{table}-{perfect}-{seller}',
                        'name': 'Rainbow Facet',
                        'rarity': 'unique',
                        'catalog_id': catalog,
                        'catalog_name': 'Rainbow Facet: ' + label,
                        'seller_id': str(seller),
                        'evidence_kind': 'ask',
                        'unit_policy': 'single_item',
                        'amount': 1,
                        'ask_ist': 10 if perfect else 1,
                        'observed_at': '2026-09-18',
                        'scope_status': 'verified',
                        'base_code': capture(spec).base_code,
                        'ethereal': False,
                        'sockets': 0,
                        'socket_contents': 'empty',
                        'properties': {
                            '799': 'softcore',
                            '800': False,
                            '798': 'PC',
                            '1854': 'reign of the warlock',
                            PROPERTIES[damage]: 5 if perfect else 3,
                            PROPERTIES[pierce]: 5 if perfect else 3,
                        },
                    }
                )
        variant['trade_qualification'] = {
            'facet_table_id': table,
            'scope': 'SC / Non-Ladder / PC / RotW',
            'basis': 'reviewed_asking_segments',
            'reviewed_at': '2026-10-02',
            'material_stats': [f'{damage}:0', f'{pierce}:0'],
            'market_stat_properties': {f'{damage}:0': PROPERTIES[damage], f'{pierce}:0': PROPERTIES[pierce]},
            'valid_if': {
                'all': [
                    {'op': 'fact_eq', 'field': field, 'value': value}
                    for field, value in [('ethereal', False), ('sockets', 0), ('socket_contents', 'empty')]
                ]
            },
            'default_status': 'candidate',
            'default_reason': label + ': ordinary roll.',
            'default_evidence_ids': [r['id'] for r in rows[:3]],
            'market_evidence': rows,
            'bands': [
                {
                    'when': variant['overrides'][0]['when'],
                    'status': 'premium',
                    'reason': label + ': both rolls perfect.',
                    'evidence_ids': [r['id'] for r in rows[3:]],
                }
            ],
        }
    return {'schema_version': 1, 'policies': [policy]}


@pytest.fixture
def reviewed(monkeypatch):
    doc = document()
    monkeypatch.setattr(named_tiers, 'read_artifact', lambda _: json.dumps(doc).encode())
    import pricing.knowledge.assessment.policies.trade_qualification as module

    monkeypatch.setattr(module, 'read_artifact', lambda _: json.dumps(doc).encode())
    return doc


@pytest.mark.parametrize('spec', VARIANTS, ids=lambda s: s[2])
@pytest.mark.parametrize(
    ('damage', 'pierce', 'expected'),
    [
        (3, 3, 'candidate'),
        (5, 4, 'candidate'),
        (4, 5, 'candidate'),
        (5, 5, 'premium'),
        (6, 5, 'unresolved'),
        (5, 2, 'unresolved'),
        (5.5, 5, 'unresolved'),
        (4.5, 5, 'unresolved'),
    ],
)
def test_variant_trade_thresholds(reviewed, spec, damage, pierce, expected):
    facts = capture(spec)
    stats = {
        **facts.stats,
        f'{spec[6]}:0': {'status': 'decoded', 'value': damage},
        f'{spec[7]}:0': {'status': 'decoded', 'value': pierce},
    }
    result = assess_trade_qualification(replace(facts, stats=stats))
    assert result['status'] == expected
    if expected != 'unresolved':
        assert spec[2] in result['reason']


@pytest.mark.parametrize('spec', VARIANTS, ids=lambda s: s[2])
@pytest.mark.parametrize('corruption', ['trigger', 'identity', 'missing_roll', 'ethereal', 'socket'])
def test_unverified_capture_gets_no_trade_credit(reviewed, spec, corruption):
    facts = capture(spec)
    if corruption == 'trigger':
        facts = replace(facts, stats={k: v for k, v in facts.stats.items() if k.split(':')[0] not in ('197', '199')})
    elif corruption == 'identity':
        facts = replace(facts, provenance={})
    elif corruption == 'missing_roll':
        facts = replace(facts, stats={k: v for k, v in facts.stats.items() if k != f'{spec[6]}:0'})
    else:
        facts = replace(facts, **({'ethereal': True} if corruption == 'ethereal' else {'sockets': 1}))
    assert assess_trade_qualification(facts)['status'] == 'unresolved'


@pytest.mark.parametrize(
    'corruption', ['catalog', 'label', 'trigger', 'other_trigger', 'table', 'missing_review', 'mixed_root']
)
def test_cannot_mix_variant_trade_evidence(corruption):
    doc = document()
    policy = doc['policies'][0]
    review = policy['variant_rules'][0]['trade_qualification']
    row = review['market_evidence'][0]
    if corruption == 'catalog':
        row['catalog_id'] = VARIANTS[4][1]  # Same element, different trigger.
    elif corruption == 'label':
        row['catalog_name'] = 'Rainbow Facet: Cold Death'
    elif corruption == 'trigger':
        row['properties']['780'] = 99
    elif corruption == 'other_trigger':
        row['properties']['785'] = 100
    elif corruption == 'table':
        review['facet_table_id'] = 396
    elif corruption == 'missing_review':
        del policy['variant_rules'][1]['trade_qualification']
    else:
        policy['trade_qualification'] = deepcopy(review)
    with pytest.raises(ValueError, match=r'[Tt]rade|[Ff]acet'):
        named_tiers._policies(json.dumps(doc).encode())


def test_actual_facet_reviews_preserve_separate_catalog_evidence():
    import hashlib

    from pricing.knowledge.date_recovery import fingerprint, verify_policy_sources

    doc = json.loads(named_tiers.RULES.read_bytes())
    policy = next(p for p in doc['policies'] if p['name'] == 'Rainbow Facet')
    raw = (named_tiers.ROOT / 'pricing/data/appraisal-market.jsonl').read_bytes()
    rows = list(map(json.loads, raw.splitlines()))
    indexed = {r['id']: r for r in rows}
    verify_policy_sources(rows, doc)
    for variant, spec in zip(policy['variant_rules'], VARIANTS, strict=True):
        review = variant['trade_qualification']
        assert review['facet_table_id'] == spec[0]
        assert review['market_snapshot']['sha256'] == hashlib.sha256(raw).hexdigest()
        for evidence in review['market_evidence']:
            original = indexed[evidence['id']]
            assert evidence['normalized_row_sha256'] == fingerprint(original)
            assert all(original.get(k) == v for k, v in evidence.items() if k != 'normalized_row_sha256')
            assert (evidence['catalog_id'], evidence['catalog_name']) == (spec[1], 'Rainbow Facet: ' + spec[2])
            perfect = all(evidence['properties'][PROPERTIES[k]] == 5 for k in spec[6:8])
            assert (evidence['id'] in review['bands'][0]['evidence_ids']) == perfect
            assert (evidence['id'] in review['default_evidence_ids']) != perfect
    named_tiers._policies(json.dumps(doc).encode())
