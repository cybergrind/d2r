from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_ethereal_death_cleaver_needs_zod_before_matching_zeal_setup():
    role = next((r for r in build()['profiles'] if r['id'] == 'zeal-death-cleaver-alternative'), None)
    assert role is not None
    item = replace(
        facts('Berserker Axe', 'unique', 'Death Cleaver'),
        ethereal=True,
        stats={
            f'{k}:0': {'status': 'decoded', 'value': v}
            for k, v in [(17, 230), (18, 230), (93, 40), (141, 66), (116, 33), (86, 6)]
        },
    )

    def assess(candidate, context=None):
        return assess_roles(candidate, [role], context or {'player_class': 'Paladin'})

    pending = assess(item)[0]
    assert pending['status'] == 'partial'
    assert any('Zod Rune' in s for s in pending['missing'])
    ready = replace(item, sockets=1, socket_contents='filled', socket_items=[{'name': 'Zod Rune'}])
    assert assess(ready)[0]['status'] == 'matched'
    assert assess(replace(ready, socket_items=[{'name': 'Shael Rune'}]))[0]['status'] == 'partial'
    assert assess(replace(ready, socket_items=[]))[0]['status'] == 'partial'
    assert assess(replace(ready, ethereal=False))[0]['status'] == 'failed'
    assert not assess(replace(ready, rarity='rare'))
    assert assess(replace(ready, base_code=facts('Hand Axe').base_code))[0]['status'] == 'failed'
    assert assess(ready, {'player_class': 'Sorceress'})[0]['status'] == 'failed'
