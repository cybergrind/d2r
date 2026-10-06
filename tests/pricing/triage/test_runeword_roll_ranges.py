import json
from pathlib import Path

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.triage.analyze_rolls import analyze
from tests.pricing.triage.test_bands import listing


def test_runeword_comparison_uses_displayed_enhancement_total():
    game = metadata()
    base = next(b for b in game['bases'].values() if b['name'] == 'Phase Blade')
    definitions = json.loads(Path('pricing/data/appraisal-definitions.json').read_text())['rows']
    definition = next(d for d in definitions if d['name'] == 'Crescent Moon' and d['rarity'] == 'runeword')
    rows = []
    for i in range(20):
        r = listing(str(i), 2, ethereal=False, socket_contents='filled', sockets=3, base_code=base['code'])
        r.update(name='Crescent Moon', category='runewords')
        r['properties']['510'] = 233 if i < 10 else 235
        rows.append(r)
    report = analyze(rows, [definition], game)[0]
    spec = report['deciding']['510']
    assert (spec['min'], spec['max']) == (180, 235)
    assert spec['sample_size'] == 20
    assert definition['roll_ranges']['17']['max'] == 220


@pytest.mark.parametrize(
    ('name', 'base_name', 'stat', 'bounds'),
    [
        ('Doom', 'Berserker Axe', '17', (330, 385)),
        ('Breath of the Dying', 'Great Poleaxe', '17', (350, 415)),
        ('Exile', 'Sacred Targe', '16', (220, 275)),
        ('Phoenix', 'Monarch', '17', (350, 400)),
    ],
)
def test_total_range_respects_rune_and_base_family(name, base_name, stat, bounds):
    from pricing.triage.runeword_ranges import total_definition

    game = metadata()
    base = next(b for b in game['bases'].values() if b['name'] == base_name)
    definitions = json.loads(Path('pricing/data/appraisal-definitions.json').read_text())['rows']
    definition = next(d for d in definitions if d['name'] == name and d['rarity'] == 'runeword')
    total = total_definition(definition, base['code'], game)['roll_ranges'][stat]
    assert (total['min'], total['max']) == bounds
    assert total_definition(definition, None, game) is definition
