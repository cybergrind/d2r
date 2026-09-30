from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('suffix', 'name', 'base', 'values'),
    [
        (
            'arm-king-leoric',
            'Arm of King Leoric',
            'Tomb Wand',
            {'188:18': 2, '188:17': 2, '107:69': 3, '107:70': 3, '105:0': 10, '217:0': 1.25},
        ),
        ('umes-lament', "Ume's Lament", 'Grim Wand', {'83:2': 2, '105:0': 20, '9:0': 40, '107:87': 2}),
        ('spirit-shroud', 'The Spirit Shroud', 'Ghost Armor', {'127:0': 1, '153:0': 1, '35:0': 7, '74:0': 10}),
    ],
)
def test_summoner_named_alternatives_highlight_their_actual_native_benefits(suffix, name, base, values):
    bundle = build()
    rid = 'summoner-necromancer-' + suffix + '-alternative'
    role = next((r for r in bundle['profiles'] if r['id'] == rid), None)
    assert role is not None
    ignored = {'16:0': 150, '112:0': 50, '107:77': 3, '107:80': 2}
    item = replace(
        facts(base, 'unique', name),
        stats={k: {'status': 'decoded', 'value': v} for k, v in {**ignored, **values}.items()},
    )
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    context = {'player_class': 'Necromancer'}

    def evaluate(candidate, ctx=context):
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
        )

    assert set(evaluate(item).annotations) == set(values)
    assert not evaluate(item, {'player_class': 'Sorceress'}).annotations
    assert not evaluate(replace(item, rarity='rare')).annotations
    if suffix == 'spirit-shroud':
        assert not evaluate(replace(item, ethereal=True)).annotations
    else:
        assert evaluate(replace(item, ethereal=True)).annotations
    from pricing.knowledge.definition_store import catalog

    d = catalog().named['unique', name]
    base_def = d['base_definition']
    chain = [base_def[k] for k in ('normcode', 'ubercode', 'ultracode')]
    allowed = chain[chain.index(d['base_code']) :]
    names = {r['code']: r['name'] for r in metadata()['bases'].values()}
    for code in allowed:
        assert evaluate(replace(item, base_code=code, base_name=names[code])).annotations
    assert not evaluate(replace(item, base_code=facts('Hand Axe').base_code)).annotations
