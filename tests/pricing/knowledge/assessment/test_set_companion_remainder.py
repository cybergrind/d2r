from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'count', 'companions', 'wrong'),
    [
        ('Angelic Halo', 'Ring', 2, ['Angelic Wings'], ['Angelic Halo', 'Angelic Halo']),
        ('Angelic Wings', 'Amulet', 3, ['Angelic Halo'], ['Angelic Wings']),
        (
            "Horazon's Secrets",
            'Occult Codex',
            1,
            ["Horazon's Dominion", "Horazon's Legacy"],
            ["Horazon's Dominion", "Horazon's Dominion"],
        ),
    ],
)
def test_set_companion_uses_require_distinct_pieces_and_preserve_element(name, base, count, companions, wrong):
    selected = [p for p in build()['profiles'] if p.get('names') == [name] and p['id'].endswith('-qualified-equipment')]
    assert len(selected) == count
    item = facts(base, 'set', name)
    for role in selected:
        context = {'player_class': role['must']['all'][0]['value'], 'player_items': companions}
        assert assess_roles(item, [role], context)[0]['dependencies'][0]['status'] == 'true'
        assert assess_roles(item, [role], {**context, 'player_items': wrong})[0]['dependencies'][0]['status'] == 'false'
        assert assess_roles(replace(item, ethereal=True), [role], context)[0]['status'] == 'failed'
        if name == "Horazon's Secrets":
            assert '333:0' in role['important_stats']
            assert '188:57' not in role['important_stats']
            assert '334:0' not in role['important_stats']
        elif name == 'Angelic Wings':
            assert '127:0' not in role['important_stats']
        else:
            assert '80:0' not in role['important_stats']
