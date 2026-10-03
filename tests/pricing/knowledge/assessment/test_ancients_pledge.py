"""Fixed cold resistance adds to fixed all-resistance in the actual recipe."""

import json
from pathlib import Path

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.runeword import RunewordHandler
from pricing.knowledge.definition_store import DefinitionStore, definition_snapshot
from pricing.knowledge.definitions import build_definitions, scalar_ranges


ROOT = Path(__file__).resolve().parents[4]
RECORDS = json.loads((Path(__file__).parent / 'fixtures/ancients_pledge.json').read_text())['records']


@pytest.fixture(scope='module')
def rebuilt(tmp_path_factory):
    path = tmp_path_factory.mktemp('pledge-definitions') / 'definitions.json'
    path.write_text(json.dumps(build_definitions(ROOT)))
    return DefinitionStore(path).load()


@pytest.mark.parametrize('record', RECORDS, ids=lambda r: r['observation']['item']['base_name'])
def test_saved_pledge_matches_fixed_recipe_plus_rune_resistance(rebuilt, record):
    facts = normalize(record['observation'])
    with definition_snapshot(rebuilt):
        contract, gaps = RunewordHandler().contract(facts, 'shield')
    assert contract is not None, gaps
    assert contract.properties['426'] == 43
    assert contract.intrinsic_properties['426'] == 43


def test_fixed_resistance_sources_add_without_collapsing_variable_rolls():
    props = json.loads((ROOT / 'third-parties/d2data/json/properties.json').read_text())
    raw_stats = json.loads((ROOT / 'third-parties/d2data/json/itemstatcost.json').read_text())
    stats = {key: row['*ID'] for key, row in raw_stats.items()}
    row = {'T1Code1': 'res-cold', 'T1Min1': 30, 'T1Max1': 30, 'T1Code2': 'res-all', 'T1Min2': 13, 'T1Max2': 13}
    ranges = scalar_ranges(row, props, stats, runeword=True)
    assert ranges['43']['min'] == ranges['43']['max'] == 43
    assert ranges['39']['min'] == ranges['41']['min'] == ranges['45']['min'] == 13
    # The shared all-resistance roll cannot be modeled as independent totals.
    assert '43' not in scalar_ranges({**row, 'T1Min2': 12}, props, stats, runeword=True)
