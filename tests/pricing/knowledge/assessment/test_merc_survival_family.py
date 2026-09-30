from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'quality', 'key'),
    [
        ('Rockfleece', 'Field Plate', 'unique', '36:0'),
        ('Lionheart', 'Mage Plate', 'normal', '7:0'),
        ('Temper', 'Crown', 'normal', '142:0'),
        ('Temper', 'Crown', 'low_quality', '142:0'),
        ('Lionheart', 'Mage Plate', 'low_quality', '7:0'),
        ('Cure', 'Crown', 'normal', '151:109'),
        ('Cure', 'Crown', 'superior', '151:109'),
        ('Cure', 'Crown', 'low_quality', '151:109'),
    ],
)
def test_early_mercenary_family_annotates_native_benefit_without_vitality_or_defense_premium(name, base, quality, key):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r['id'].endswith('-early-merc-' + name.lower())]
    assert len(roles) == {'Rockfleece': 22, 'Lionheart': 23, 'Temper': 23, 'Cure': 17}[name]
    for role in roles:
        item = replace(
            facts(base, quality, name), stats={k: {'status': 'decoded', 'value': 1} for k in [key, '3:0', '16:0']}
        )
        if quality in ('normal', 'superior', 'low_quality'):
            item = replace(item, runeword=name, sockets=3, socket_contents='filled')
        context = {'player_class': role['must']['all'][0]['value']}
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]
        result = StatsEvaluator().evaluate(
            item, configs, context, role_outcomes=assess_role_results(item, [role], context)
        )
        assert set(result.annotations) == {key}
    assert bundle['guide_demand']['summaries'][name]['alternative_builds']


def test_early_mercenary_source_links_retain_the_ledger_variant_name():
    from pricing.knowledge.assessment.maintenance.inventory import audit_occurrences

    profiles = [r for r in build()['profiles'] if '-early-merc-' in r['id'] and r['variant'] == 'early']
    assert len(profiles) >= 85
    rows = [
        {
            'id': p['id'],
            'name': p['names'][0],
            'build': p['build'],
            'variant': 'early',
            'side': 'merc',
            'slot': p['slot'],
            'source_id': p['source']['path'],
            'source_locator': p['source']['locator'],
            'details': {'recommended': True, 'resolution_status': 'resolved'},
        }
        for p in profiles
    ]
    audit = audit_occurrences(rows, profiles)
    assert audit['counts']['with_source_rules'] == len(profiles)
