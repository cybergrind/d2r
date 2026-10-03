from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance import trade_arachnid_evidence as evidence
from tests.pricing.knowledge.assessment.policies.test_market_ethereal_inference import listing


def row(seller, ed=120):
    r = listing(ed)
    r.update(
        id=f'row-{seller}-{ed}',
        seller_id=seller,
        scope_status='verified',
        evidence_kind='ask',
        amount=1,
        unit_policy='single_item',
        ask_ist=2.0,
        observed_at='2026-09-18',
    )
    r['properties'].update({'799': 'softcore', '800': False, '798': 'PC', '1854': 'reign of the warlock'})
    return r


def test_perfect_and_lower_censuses_count_independent_sellers_and_keep_unknowns_separate():
    rows = [row('a'), row('b'), row('c'), row('a', 119), row('x', 110)]
    unknown = row('u')
    unknown['properties'].pop('1855')
    rows.append(unknown)
    rows.append(deepcopy(rows[0]))
    result = evidence.audit_arachnid(rows)
    assert result['cohorts']['perfect']['priced_sellers'] == ['a', 'b', 'c']
    assert result['cohorts']['lower']['priced_sellers'] == ['a', 'x']
    assert result['cohorts']['unproven']['priced_sellers'] == ['u']
    assert evidence.reviewed_variants(result)
    new = row('new', 110)
    new['ethereal'] = False
    new['properties'].pop('1855')
    assert not evidence.reviewed_variants(evidence.audit_arachnid([*rows, new]))


@pytest.mark.parametrize('mutation', ['ladder', 'hardcore', 'bulk', 'bool-amount', 'price', 'date', 'ed', 'socket'])
def test_incompatible_or_malformed_rows_do_not_supply_market_evidence(mutation):
    r = row('bad')
    if mutation == 'ladder':
        r['properties']['800'] = True
    elif mutation == 'hardcore':
        r['properties']['799'] = 'hardcore'
    elif mutation == 'bulk':
        r['amount'] = 2
    elif mutation == 'bool-amount':
        r['amount'] = True
    elif mutation == 'price':
        r['ask_ist'] = float('inf')
    elif mutation == 'date':
        r['observed_at'] = None
    elif mutation == 'ed':
        r['properties']['425'] = 130
    else:
        r['sockets'] = 1
    result = evidence.audit_arachnid([r])
    assert not any(c['priced_rows'] for c in result['cohorts'].values())


def test_actual_cache_has_four_perfect_sellers_but_only_two_proved_lower_sellers():
    import json
    from pathlib import Path

    result = evidence.audit_arachnid(json.loads(s) for s in Path(evidence.MARKET).read_text().splitlines())
    assert len(result['cohorts']['perfect']['priced_sellers']) == 4
    assert len(result['cohorts']['lower']['priced_sellers']) == 2
    assert evidence.reviewed_variants(result)


def test_loader_pins_market_bytes_and_uses_the_selected_definition(tmp_path, monkeypatch):
    import hashlib
    import json

    from pricing.knowledge.assessment.policies import market_ethereal_inference
    from tests.pricing.knowledge.assessment.maintenance.test_fixed_armor_trade_reviews import inputs

    identity = ('unique', 'Arachnid Mesh')
    _, definitions, _ = inputs(identity)
    path = tmp_path / evidence.MARKET
    path.parent.mkdir(parents=True)
    raw = '\n'.join(json.dumps(row(seller)) for seller in ('a', 'b', 'c')).encode()
    path.write_bytes(raw)
    policies = {
        identity: {
            'trade_qualification': {
                'market_snapshot': {
                    'path': evidence.MARKET,
                    'sha256': hashlib.sha256(raw).hexdigest(),
                }
            }
        }
    }
    scope = {'native_unique_caster_belt'}
    doc = {'rows': [{'quality': 'unique', 'name': 'Arachnid Mesh', 'scope': next(iter(scope))}]}
    # Global/staged definitions are not the authority for this selected review.
    monkeypatch.setattr(market_ethereal_inference, 'named_definitions', dict)
    result = evidence.load_evidence(tmp_path, doc, policies, scope, {identity: definitions})
    assert evidence.reviewed_variants(result[identity])
    path.write_bytes(raw + b'\n')
    assert evidence.load_evidence(tmp_path, doc, policies, scope, {identity: definitions}) == {}
