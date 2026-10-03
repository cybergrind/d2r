import copy

import pytest

from pricing.knowledge.date_recovery import recover_rows


OLD = '1' * 64
NEW = '2' * 64


def rows():
    original = {
        'id': 'old-id',
        'source': 'cache',
        'listing_id': '1',
        'observed_at': None,
        'observation_date_basis': 'unknown',
        'properties': {'441': 20},
        'ask_ist': 1,
        'facet_basis': {
            'base_code': {
                'kind': 'named_definition',
                'path': 'pricing/data/appraisal-definitions.json',
                'generation': OLD,
            }
        },
    }
    current = copy.deepcopy(original)
    current.update(
        id='new-id',
        observed_at='2026-09-18',
        observation_date_basis='documented_collection',
        observation_date_precision='day',
        observation_date_source={'document': 'reviewed'},
    )
    current['facet_basis']['base_code']['generation'] = NEW
    return original, current


def test_date_recovery_preserves_existing_facets_prices_and_unrelated_records():
    old, new = rows()
    unrelated = {'id': 'untouched'}
    output, proof = recover_rows([old, unrelated], [new], NEW)
    assert output[0]['observed_at'] == '2026-09-18'
    assert output[0]['id'] == 'new-id'
    assert output[0]['facet_basis'] == old['facet_basis']
    assert output[0]['properties'] == old['properties']
    assert output[0]['ask_ist'] == old['ask_ist']
    assert output[1] is unrelated
    assert old['observed_at'] is None
    assert len(proof) == 1
    assert proof[0]['old_id'] == 'old-id'


@pytest.mark.parametrize(
    'mutation',
    [
        'property',
        'price',
        'facet-kind',
        'facet-value',
        'unreviewed-generation',
        'date-conflict',
        'absent-old',
        'duplicate-old',
        'colliding-id',
    ],
)
def test_date_recovery_refuses_material_or_identity_changes(mutation):
    old, new = rows()
    existing = [old]
    if mutation == 'property':
        new['properties']['441'] = 19
    if mutation == 'price':
        new['ask_ist'] = 2
    if mutation == 'facet-kind':
        new['facet_basis']['base_code']['kind'] = 'other'
    if mutation == 'facet-value':
        new['base_code'] = 'changed'
    if mutation == 'unreviewed-generation':
        new['facet_basis']['base_code']['generation'] = OLD
    if mutation == 'date-conflict':
        old['observed_at'] = '2026-09-19'
    if mutation == 'absent-old':
        existing = []
    if mutation == 'duplicate-old':
        existing.append(copy.deepcopy(old))
    if mutation == 'colliding-id':
        existing.append({'id': new['id']})
    with pytest.raises(ValueError, match=r'observation|evidence|generation'):
        recover_rows(existing, [new], NEW)
    assert 'observation_date_source' not in old


def test_recovery_is_idempotent_without_rewriting_original_facet_provenance():
    old, new = rows()
    output, _ = recover_rows([old], [new], NEW)
    again, changes = recover_rows(output, [new], NEW)
    assert again == output
    assert not changes


@pytest.mark.parametrize('with_digest', [True, False])
def test_source_verification_includes_nested_variant_reviews(with_digest):
    from pricing.knowledge.date_recovery import fingerprint, verify_policy_sources

    row = {'id': 'facet', 'ask_ist': 1}
    evidence = {**row, **({'normalized_row_sha256': fingerprint(row)} if with_digest else {})}
    doc = {
        'policies': [
            {'name': 'Rainbow Facet', 'variant_rules': [{'trade_qualification': {'market_evidence': [evidence]}}]}
        ]
    }
    verify_policy_sources([row], doc)
    with pytest.raises(ValueError, match='reviewed trade evidence'):
        verify_policy_sources([{**row, 'ask_ist': 100}], doc)


def test_unhashed_partial_evidence_cannot_certify_a_full_market_row():
    from pricing.knowledge.date_recovery import verify_policy_sources

    row = {'id': 'sample', 'ask_ist': 1, 'observed_at': '2026-10-02'}
    doc = {'policies': [{'name': 'Sample', 'trade_qualification': {'market_evidence': [{'id': 'sample'}]}}]}
    with pytest.raises(ValueError, match='reviewed trade evidence'):
        verify_policy_sources([row], doc)
