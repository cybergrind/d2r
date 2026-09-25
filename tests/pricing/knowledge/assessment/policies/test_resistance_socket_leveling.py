from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.policies.leveling import assess_leveling
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def setup(base, name, fillers, stats):
    bases = {b['name']: b for b in metadata()['bases'].values()}
    return replace(
        facts(base, 'unique' if name else 'normal', name),
        sockets=len(fillers),
        socket_contents='filled',
        socket_items=[
            {'base_code': bases[n]['code'], 'name': n, 'unit_id': i + 1, 'position': i} for i, n in enumerate(fillers)
        ],
        stats={f'{s}:0': {'status': 'decoded', 'value': v} for s, v in stats.items()},
    )


@pytest.mark.parametrize(
    ('item', 'index'),
    [
        (setup('Mask', None, ['Ral Rune', 'Ort Rune', 'Thul Rune'], {39: 30, 41: 30, 43: 30}), 5),
        (
            setup(
                'Round Shield',
                "Moser's Blessed Circle",
                ['Perfect Diamond', 'Ort Rune'],
                {39: 44, 41: 79, 43: 44, 45: 44},
            ),
            9,
        ),
        (setup('Sallet', 'Rockstopper', ['Perfect Ruby'], {7: 38}), 10),
    ],
)
def test_reviewed_socket_survival_setups_require_actual_fillers(item, index):
    locator = f'/generic_patterns/{index}'
    matches = [u for u in assess_leveling(item) if u['source']['locator'] == locator]
    assert len(matches) == 1
    assert matches[0]['status'] == 'conditional'
    for changed in [
        replace(item, socket_items=[]),
        replace(item, stats={}),
        replace(item, socket_contents='empty'),
        replace(item, runeword='unverified'),
    ]:
        assert not any(u['source']['locator'] == locator for u in assess_leveling(changed))


def test_resistance_helm_requires_all_three_runes_and_their_totals():
    item = setup('Mask', None, ['Ral Rune', 'Ral Rune', 'Ral Rune'], {39: 90})
    assert any(u['source']['locator'] == '/generic_patterns/5' for u in assess_leveling(item))
    for changed in [
        replace(item, stats={'39:0': {'status': 'decoded', 'value': 30}}),
        replace(item, socket_items=item.socket_items[:2]),
    ]:
        assert not assess_leveling(changed)


def test_reviewed_gem_constants_match_pinned_effects():
    import json
    from pathlib import Path

    from pricing.knowledge.assessment.policies.socket_leveling import DIAMONDS, RESIST_RUNES, RUBIES

    path = Path(__file__).resolve().parents[5] / 'third-parties/d2data/json/gems.json'
    rows = {r['name']: r for r in json.loads(path.read_text()).values()}
    for name, amount in DIAMONDS.items():
        assert rows[name]['shieldMod1Code'] == 'res-all'
        assert rows[name]['shieldMod1Min'] == rows[name]['shieldMod1Max'] == amount
    for name, amount in RUBIES.items():
        assert rows[name]['helmMod1Code'] == 'hp'
        assert rows[name]['helmMod1Min'] == rows[name]['helmMod1Max'] == amount
    for name in RESIST_RUNES:
        assert rows[name]['helmMod1Min'] == rows[name]['helmMod1Max'] == 30
        assert rows[name]['shieldMod1Min'] == rows[name]['shieldMod1Max'] == 35
