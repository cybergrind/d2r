from dataclasses import replace

import pytest

from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def raven(dex=20, ar=250):
    return replace(
        facts('Ring', 'unique', 'Raven Frost'),
        stats={f'{key}:0': {'status': 'decoded', 'value': value} for key, value in ((2, dex), (19, ar))},
    )


@pytest.mark.parametrize(
    ('dex', 'ar', 'status'),
    [(15, 150, 'candidate'), (19, 250, 'candidate'), (20, 249, 'candidate'), (20, 250, 'premium')],
)
def test_raven_requires_both_material_rolls_for_premium(dex, ar, status):
    result = assess_trade_qualification(raven(dex, ar))
    assert result['status'] == status
    assert result['material_stats'] == ['2:0', '19:0']
    assert result['basis'] == 'reviewed_asking_segments'
    assert 'price_estimate' not in result


@pytest.mark.parametrize(
    'changes',
    [
        {'stats': {}},
        {'ethereal': None},
        {'ethereal': True},
        {'identified': False},
        {'sockets': None},
        {'sockets': 1},
        {'socket_contents': 'unknown'},
    ],
)
def test_unknown_or_invalid_raven_never_gets_trade_credit(changes):
    assert assess_trade_qualification(replace(raven(), **changes))['status'] == 'unresolved'


@pytest.mark.parametrize(('dex', 'ar'), [(21, 250), (20, 251), (14, 150), (20, 149)])
def test_out_of_range_rolls_never_get_trade_credit(dex, ar):
    assert assess_trade_qualification(raven(dex, ar))['status'] == 'unresolved'


def test_unreviewed_identity_gets_no_invented_qualification():
    assert assess_trade_qualification(facts('Ring', 'unique', "Nature's Peace")) == {}


@pytest.mark.parametrize(
    'name',
    [
        'Raven Frost',
        'Wisp Projector',
        "Titan's Revenge",
        "Bul-Kathos' Wedding Band",
        'The Stone of Jordan',
        "Tal Rasha's Adjudication",
        "Mara's Kaleidoscope",
        'Sandstorm Trek',
        'Nagelring',
        'Metalgrid',
        "Trang-Oul's Girth",
        "Trang-Oul's Claws",
        "Immortal King's Pillar",
        "Tal Rasha's Fine-Spun Cloth",
        "Gheed's Fortune",
        "Highlord's Wrath",
        'Sling',
        'Entropy Locket',
        'Opalvein',
        "Defender's Fire",
        "Defender's Bile",
        "Guardian's Light",
        "Guardian's Thunder",
        'Hellfire Torch',
        'Dwarf Star',
        "Protector's Frost",
        "Protector's Stone",
        "Horazon's Legacy",
        'Flame Rift',
        'Crack of the Heavens',
        'Cold Rupture',
        'Rotting Fissure',
        'Black Cleft',
        'Bone Break',
        'Annihilus',
    ],
)
def test_scoped_asking_evidence_is_exactly_preserved_from_offline_snapshot(name):
    import hashlib
    import json

    from pricing.knowledge.assessment.policies.named_tiers import ROOT, RULES
    from pricing.knowledge.assessment.policies.trade_qualification import validate_review

    policy = next(r for r in json.loads(RULES.read_bytes())['policies'] if r['name'] == name)
    review = policy['trade_qualification']
    raw = (ROOT / review['market_snapshot']['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == review['market_snapshot']['sha256']
    original = {r['id']: r for r in map(json.loads, raw.splitlines())}
    for row in review['market_evidence']:
        evidence = original[row['id']]
        if name == 'Hellfire Torch':
            assert row['properties']['453'] == 3
            assert set(row['properties']) & {'453', '514', '498', '442', '403', '488', '519', '1862'} == {'453'}
        assert all(evidence.get(key) == value for key, value in row.items() if key != 'normalized_row_sha256')
        assert (
            hashlib.sha256(json.dumps(evidence, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            == row['normalized_row_sha256']
        )
        is_perfect = (
            (row['properties']['429'], row['properties']['423']) == (20, 250)
            if name == 'Raven Frost'
            else (row['properties']['689'], row['properties']['461']) == (20, 20)
            if name == 'Wisp Projector'
            else row['properties']['510'] >= 190
            if name == "Titan's Revenge"
            else row['properties']['462'] == 5
            if name == "Bul-Kathos' Wedding Band"
            else (row['properties']['437'], row['properties']['582']) == (15, 15)
            if name == 'Sandstorm Trek'
            else row['properties']['461'] == 40
            if name == "Gheed's Fortune"
            else row['properties']['400'] == 50
            if name == "Trang-Oul's Girth"
            else row['properties']['1877'] == 5
            if name == 'Sling'
            else row['properties']['750'] == row['properties']['735'] == 10
            if name == "Defender's Fire"
            else row['properties']['783'] == row['properties']['723'] == 10
            if name == "Defender's Bile"
            else row['properties']['1879'] == row['properties']['1877'] == 10
            if name == "Guardian's Light"
            else row['properties']['743'] == row['properties']['736'] == 10
            if name == "Guardian's Thunder"
            else abs(row['properties']['426']) == 70
            if name == 'Cold Rupture'
            else abs(row['properties']['936']) == 45
            if name == 'Black Cleft'
            else row['properties']['1223'] == 10
            if name == 'Bone Break'
            else False
        )
        expected_band = (
            (1 if row['properties']['930'] == 'Elite' else 0)
            if name == "Titan's Revenge"
            else 0
            if name in {'Nagelring', "Tal Rasha's Fine-Spun Cloth"}
            else (0 if row['properties']['441'] == 30 else 1)
            if name == "Mara's Kaleidoscope"
            else (0 if min(row['properties']['727'], row['properties']['441']) >= 19 else None)
            if name == 'Annihilus'
            else (0 if is_perfect else None)
        )
        assert [i for i, band in enumerate(review['bands']) if row['id'] in band['evidence_ids']] == (
            [] if expected_band is None else [expected_band]
        )
        assert (row['id'] in review['default_evidence_ids']) == (expected_band is None)
    validate_review(review, (policy['quality'], name), policy['valid_if'])


@pytest.mark.parametrize('corruption', ['scope', 'identity', 'seller', 'band'])
def test_trade_review_cannot_use_foreign_mode_identity_or_duplicate_sellers(corruption):
    import json

    from pricing.knowledge.assessment.policies.named_tiers import RULES
    from pricing.knowledge.assessment.policies.trade_qualification import validate_review

    policy = next(r for r in json.loads(RULES.read_bytes())['policies'] if r['name'] == 'Raven Frost')
    review = policy['trade_qualification']
    if corruption == 'scope':
        review['market_evidence'][0]['properties']['800'] = True
    elif corruption == 'identity':
        review['market_evidence'][0]['name'] = 'Nagelring'
    elif corruption == 'band':
        review['bands'][0]['evidence_ids'] = ['missing']
    else:
        for row in review['market_evidence']:
            row['seller_id'] = 'one-seller'
    with pytest.raises(ValueError, match='trade'):
        validate_review(review, ('unique', 'Raven Frost'), policy['valid_if'])


@pytest.mark.parametrize(
    'corruption', ['swapped_bands', 'unknown_ethereal', 'unknown_roll', 'wrong_mapping', 'wrong_base']
)
def test_trade_band_evidence_must_match_its_native_roll_and_variant_predicates(corruption):
    import json

    from pricing.knowledge.assessment.policies.named_tiers import RULES, _policies

    document = json.loads(RULES.read_bytes())
    review = next(r for r in document['policies'] if r['name'] == 'Raven Frost')['trade_qualification']
    if corruption == 'swapped_bands':
        review['default_evidence_ids'], review['bands'][0]['evidence_ids'] = (
            review['bands'][0]['evidence_ids'],
            review['default_evidence_ids'],
        )
    elif corruption == 'unknown_ethereal':
        review['market_evidence'][0]['ethereal'] = None
    elif corruption == 'unknown_roll':
        review['market_evidence'][0]['properties'].pop('429')
    elif corruption == 'wrong_base':
        review['market_evidence'][0]['base_code'] = facts('Amulet').base_code
    else:
        review['market_stat_properties'] = {'2:0': '423', '19:0': '429'}
    with pytest.raises(ValueError, match='trade'):
        _policies(json.dumps(document).encode())
