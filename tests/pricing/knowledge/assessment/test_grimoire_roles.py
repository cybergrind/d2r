from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from tests.pricing.knowledge.assessment.role_rows import role_rows
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def grimoire(completed):
    return replace(
        facts('Grimoire'),
        name='Rhyme' if completed else None,
        runeword='Rhyme' if completed else None,
        sockets=2,
        socket_contents='filled' if completed else 'empty',
        stats={f'107:{skill}': {'status': 'decoded', 'value': 1} for skill in (392, 389, 377)},
    )


@pytest.mark.parametrize('completed', [False, True])
def test_mirrored_starter_grimoire_separates_preparation_from_completed_gear(completed):
    role_id = 'mirrored-starter-rhyme-grimoire' + ('' if completed else '-base')
    profile = next((p for p in build()['profiles'] if p['id'] == role_id), None)
    assert profile is not None
    context = {'player_class': 'Warlock'}
    item = grimoire(completed)
    assert role_rows(item, [profile], context)[0]['rule_trace']['truth'] == 'true'
    for changed in (replace(item, sockets=1), replace(item, ethereal=True), grimoire(not completed)):
        results = role_rows(changed, [profile], context)
        assert not results or results[0]['status'] == 'failed'
    for skill in (392, 389, 377):
        changed = replace(item, stats={k: v for k, v in item.stats.items() if k != f'107:{skill}'})
        assert role_rows(changed, [profile], context)[0]['status'] == 'failed'
    wrong_purge = replace(
        item,
        stats={**{k: v for k, v in item.stats.items() if k != '107:389'}, '107:404': {'status': 'decoded', 'value': 3}},
    )
    assert role_rows(wrong_purge, [profile], context)[0]['status'] == 'failed'
    assert role_rows(item, [profile], {'player_class': 'Necromancer'})[0]['status'] == 'failed'
