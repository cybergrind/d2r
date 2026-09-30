from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('suffix', 'fillers', 'values'),
    [
        ('cham', ['Cham Rune'], {'153:0': 1}),
        ('um', ['Um Rune'], {'39:0': 15, '41:0': 15, '43:0': 15, '45:0': 15}),
        ('ber', ['Ber Rune'], {'36:0': 8}),
        ('ruby', ['Jewel'], {'17:0': 31, '18:0': 31, '93:0': 15}),
        ('topazes', ['Perfect Topaz'] * 3, {'80:0': 72}),
        ('resistance', ['Ral Rune', 'Ort Rune', 'Thul Rune'], {'39:0': 30, '41:0': 30, '43:0': 30}),
    ],
)
def test_zeal_helm_socket_setup_requires_actual_recipient_and_payload(suffix, fillers, values):
    bundle = build()
    rid = 'zeal-paladin-socket-helm-' + suffix
    roles = [r for r in bundle['profiles'] if r['id'] == rid]
    assert len(roles) == 1
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    mask = len(fillers) == 3
    item = facts('Mask') if mask else facts('Winged Helm', 'set', "Guillaume's Face")
    native = {} if mask else {'136:0': 35, '141:0': 15, '99:0': 30, '0:0': 15}
    bases = {b['name']: b for b in metadata()['bases'].values()}
    children = [
        {
            'name': name,
            'base_code': bases[name]['code'],
            'item_type': bases[name]['type'],
            'unit_id': i + 1,
            'position': i,
            'stats_complete': True,
            'stats': {k: {'status': 'decoded', 'value': v} for k, v in values.items()} if suffix == 'ruby' else {},
        }
        for i, name in enumerate(fillers)
    ]
    item = replace(
        item,
        sockets=len(fillers),
        socket_contents='filled',
        socket_items=children,
        stats={k: {'status': 'decoded', 'value': v} for k, v in {**native, **values}.items()},
    )

    def evaluate(candidate, klass='Paladin'):
        ctx = {'player_class': klass}
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, roles, ctx)
        )

    assert set(evaluate(item).annotations) == set(native) | set(values)
    for patch in (
        {'socket_contents': 'empty'},
        {'socket_items': []},
        {'ethereal': True},
        {'rarity': 'rare'},
        {
            'socket_items': [
                {
                    **c,
                    'base_code': bases['Perfect Amethyst']['code'],
                    'name': 'Perfect Amethyst',
                    'item_type': bases['Perfect Amethyst']['type'],
                }
                for c in children
            ]
        },
    ):
        assert not evaluate(replace(item, **patch)).annotations
    assert not evaluate(item, 'Sorceress').annotations
    if suffix == 'ruby':
        weak = {
            **children[0],
            'stats': {
                '17:0': {'status': 'decoded', 'value': 30},
                '18:0': {'status': 'decoded', 'value': 30},
                '93:0': {'status': 'decoded', 'value': 15},
            },
        }
        assert not evaluate(replace(item, socket_items=[weak])).annotations
    if mask:
        assert not assess_role_results(
            replace(item, base_code=facts('Crown').base_code), roles, {'player_class': 'Paladin'}
        )
        assert not evaluate(replace(item, socket_items=[{**c, 'unit_id': 1} for c in children])).annotations
