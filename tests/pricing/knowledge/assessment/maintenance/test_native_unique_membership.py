from dataclasses import replace

from pricing.knowledge.assessment.maintenance.profile_templates import expand_profile
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_rockfleece_mercenary_membership_requires_native_or_upgraded_base():
    role = expand_profile(
        {
            'id': 'example',
            'template': 'merc_survival',
            'item': 'Rockfleece',
            'class': 'Sorceress',
            'build': 'blizzard-sorceress',
            'variant': 'early',
            'side': 'merc',
            'slot': 'Body Armor',
            'source': {},
        }
    )
    item = facts('Field Plate', 'unique', 'Rockfleece')

    def truth(candidate):
        return assess_roles(candidate, [role], {'player_class': 'Sorceress'})[0]['rule_trace']['truth']

    assert truth(item) == 'true'
    assert truth(replace(item, base_code=facts('Quilted Armor').base_code)) == 'false'
    for base in ('Sharktooth Armor', 'Kraken Shell'):
        assert truth(replace(item, base_code=facts(base).base_code)) == 'true'
