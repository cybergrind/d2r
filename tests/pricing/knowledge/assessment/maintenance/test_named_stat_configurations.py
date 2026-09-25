from copy import deepcopy
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.domain.facts import thaw
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.roles.predicates import evaluate
from pricing.knowledge.assessment.stat_bundle import configuration_from_row, configuration_row
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def review(role):
    return {
        'id': 'named-stats',
        'version': 1,
        'role_id': role['id'],
        'profile_fingerprint': fingerprint(role),
        'review_date': '2026-09-25',
        'review_state': 'reviewed',
        'rationale': 'Reviewed mana support role',
        'priorities': [
            {
                'key': '151:120',
                'desirability': 'desirable',
                'activation': {'op': 'stat_at_least', 'key': '151:120', 'value': 12},
                'explanation': 'Mana support aura',
            }
        ],
    }


def test_named_compiler_binds_identity_independently_of_role_outcome():
    role = next(p for p in build()['profiles'] if p['id'] == 'lightning-starter-insight-merc')
    (config,) = compile_stat_configurations([review(role)], [role], root=ROOT)
    config = configuration_from_row(configuration_row(config))
    item = replace(
        facts('Bill', name='Insight'),
        runeword='Insight',
        sockets=4,
        socket_contents='filled',
        stats={'151:120': {'status': 'decoded', 'value': 12}},
    )
    assert evaluate(thaw(config.required), item).truth == 'true'
    for changes, truth in [
        ({'name': 'Infinity'}, 'false'),
        ({'name': None}, 'unknown'),
        ({'runeword': 'Infinity'}, 'false'),
        ({'runeword': None}, 'unknown'),
        ({'socket_contents': 'empty'}, 'false'),
        ({'sockets': None}, 'unknown'),
    ]:
        assert evaluate(thaw(config.required), replace(item, **changes)).truth == truth


@pytest.mark.parametrize('field', ['must', 'types'])
def test_named_compiler_cannot_invent_missing_role_requirements(field):
    role = deepcopy(next(p for p in build()['profiles'] if p['id'] == 'lightning-starter-insight-merc'))
    del role[field]
    with pytest.raises(ValueError, match='explicit'):
        compile_stat_configurations([review(role)], [role])
