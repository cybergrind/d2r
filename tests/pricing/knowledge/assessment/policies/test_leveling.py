from dataclasses import replace

from pricing.knowledge.assessment.handlers.definitions import named_definitions
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_leveling_uses_reviewed_identity_and_does_not_infer_trade_value():
    from pricing.knowledge.assessment.policies.leveling import assess_leveling

    item = facts('Heavy Gloves', 'unique', 'Bloodfist')
    uses = assess_leveling(item)
    assert uses
    assert uses[0]['tier'] == 'high'
    assert uses[0]['required_level'] == 9
    assert 'price' not in uses[0]
    assert assess_leveling(replace(item, identified=None)) == []
    assert assess_leveling(replace(item, rarity='rare')) == []
    assert assess_leveling(facts('Long Sword', 'unique', 'Bloodfist')) == []


def test_set_leveling_benefits_keep_companion_requirements():
    from pricing.knowledge.assessment.policies.leveling import assess_leveling

    uses = assess_leveling(facts('Leather Gloves', 'set', "Death's Hand"))
    assert uses
    assert uses[0]['status'] == 'conditional'
    assert any("Death's Guard" in c for c in uses[0]['conditions'])


def test_upgraded_or_socketed_item_does_not_inherit_original_equip_requirements():
    from pricing.knowledge.assessment.policies.leveling import assess_leveling

    upgraded = upgraded_bloodfist()
    assert assess_leveling(upgraded)[0]['required_level'] is None
    socketed = replace(facts('Shako', 'unique', 'Harlequin Crest'), sockets=1, socket_contents='filled')
    # No invented leveling recommendation when the corpus has none.
    assert assess_leveling(socketed) == []


def test_leveling_report_is_highlighted_in_shared_terminal_and_osd_document():
    from inventory_tracking.appraisal.presentation import ItemAssessment
    from inventory_tracking.presentation import Tone
    from pricing.knowledge.assessment.engine import assess

    item = facts('Heavy Gloves', 'unique', 'Bloodfist')
    extraction = {'item': item.to_dict(), 'decoded_stats': [], 'source': {'stat_capture_complete': True}}
    result = {
        'extraction': extraction,
        'assessment': assess(extraction, profiles=[]),
        'decision': {'price_status': 'unknown'},
    }
    doc = ItemAssessment.from_record({'state': 'complete', 'request_id': 1, 'result': result})
    lines = [line for line in doc.to_osd() if line.text.startswith('Leveling:')]
    assert lines
    assert lines[0].tone == Tone.LEVELING
    assert 'high' in lines[0].text
    assert doc.to_text() == doc.to_rich().plain


def test_leveling_keeps_value_but_reports_current_wearer_level_shortfall():
    from inventory_tracking.appraisal.sections import leveling_lines
    from pricing.knowledge.assessment.policies.leveling import assess_leveling

    item = facts('Heavy Gloves', 'unique', 'Bloodfist')
    use = assess_leveling(item, loadout={'player_level': 5})[0]
    assert use['tier'] == 'high'
    assert use['requirements_fit']['status'] == 'unmet'
    assert use['requirements_fit']['shortfalls'] == ['Player level 5; requires 9.']
    assert 'Player level 5; requires 9.' in '\n'.join(leveling_lines({'assessment': {'leveling': [use]}}))
    ready = assess_leveling(item, loadout={'player_level': 9})[0]
    assert ready['requirements_fit']['status'] == 'met'
    unknown = assess_leveling(item)[0]
    assert unknown['requirements_fit']['status'] == 'unknown'
    upgraded = assess_leveling(upgraded_bloodfist(), loadout={'player_level': 99})[0]
    assert upgraded['requirements_fit']['status'] == 'unknown'


def test_engine_passes_player_context_to_leveling_policy():
    from pricing.knowledge.assessment.engine import assess

    item = facts('Heavy Gloves', 'unique', 'Bloodfist')
    extraction = {'item': item.to_dict(), 'decoded_stats': [], 'source': {'stat_capture_complete': True}}
    result = assess(extraction, profiles=[], loadout={'player_level': 5})
    assert result['leveling'][0]['requirements_fit']['status'] == 'unmet'


def test_leveling_uses_pinned_facts_and_recommendations_until_next_assessment(tmp_path, monkeypatch):
    from pricing.knowledge.artifacts import artifact_snapshot
    from pricing.knowledge.assessment.policies import leveling

    paths = []
    for name in ('appraisal-recommendations.json', 'appraisal-item-facts.json'):
        path = tmp_path / name
        path.write_bytes((leveling.DATA / name).read_bytes())
        paths.append(path)
    monkeypatch.setattr(leveling, 'DATA', tmp_path)
    item = facts('Heavy Gloves', 'unique', 'Bloodfist')
    with artifact_snapshot(paths):
        for path in paths:
            path.write_text('{"schema_version": 1, "rows": []}')
        assert leveling.assess_leveling(item)[0]['required_level'] == 9
    assert leveling.assess_leveling(item) == []


def upgraded_bloodfist():
    definition = named_definitions()['unique', 'Bloodfist']
    return replace(
        facts('Sharkskin Gloves', 'unique', 'Bloodfist'),
        provenance={'capture': {'item_identity': {'table': 'unique', 'table_id': definition['table_id']}}},
    )
