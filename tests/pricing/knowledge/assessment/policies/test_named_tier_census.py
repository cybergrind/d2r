import hashlib
import json

import pytest

from pricing.knowledge.assessment.policies.named_tiers import ROOT, RULES, _policies
from pricing.knowledge.assessment.policies.sources import source_error
from pricing.knowledge.definition_store import catalog


def test_every_named_definition_has_a_policy_or_explicit_native_disposition():
    policies = _policies(RULES.read_bytes())
    review = json.loads((RULES.parent / 'named_tier_reviews.json').read_text())
    dispositions = {(r['quality'], r['name']): r for r in review['non_trade_definitions']}
    assert not policies.keys() & dispositions.keys()
    assert policies.keys() | dispositions.keys() == catalog().named.keys()
    for identity, policy in policies.items():
        assert source_error(policy['source'], identity, ROOT) is None, identity
    for identity, row in dispositions.items():
        definition = catalog().named[identity]
        native = definition['game_definition']
        assert definition['table_id'] == row['table_id']
        if row['kind'] == 'quest_item':
            assert definition['base_definition']['quest'] == row['base_quest']
        elif row['kind'] == 'definition_placeholder':
            assert not any(native.get(f'prop{i}') for i in range(1, 13))
        else:
            assert row['kind'] == 'disabled_definition'
            assert native['spawnable'] == 0


def test_reviewed_inputs_are_pinned_and_still_match_local_evidence():
    review = json.loads((RULES.parent / 'named_tier_reviews.json').read_text())
    for path, digest in review['inputs'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path


@pytest.mark.parametrize('change', ['duplicate', 'foreign', 'missing'])
def test_variant_tier_rules_cannot_omit_or_borrow_another_identity(change):
    document = json.loads(RULES.read_bytes())
    policy = next(p for p in document['policies'] if p['name'] == 'Rainbow Facet')
    variants = policy['variant_rules']
    if change == 'duplicate':
        variants[1]['table_ids'] = variants[0]['table_ids']
    elif change == 'foreign':
        variants[0]['table_ids'] = [catalog().named['unique', 'Hellplague']['table_id']]
    else:
        variants.pop()
    with pytest.raises(ValueError, match=r'[Vv]ariant'):
        _policies(json.dumps(document).encode())


def test_azurewrath_review_uses_active_phase_blade_instead_of_disabled_legacy_definition():
    definition = catalog().named['unique', 'Azurewrath']
    assert definition['table_id'] == 301
    assert definition['base_definition']['name'] == 'Phase Blade'
    assert definition['game_definition']['spawnable'] == 1
    review = json.loads((RULES.parent / 'named_tier_reviews.json').read_text())['rows']['unique:Azurewrath']
    policy = _policies(RULES.read_bytes())['unique', 'Azurewrath']
    baseline = next(
        row
        for row in json.loads((RULES.parent / 'named_baselines.json').read_text())['rows']
        if row['name'] == 'Azurewrath' and row['quality'] == 'unique'
    )
    for text in (review['basis'], policy['review'], baseline['basis']):
        assert 'Phase Blade' in text
        assert 'Sanctuary' in text
        assert 'disabled' in text
