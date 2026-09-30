from inventory_tracking.appraisal.presentation import ItemAssessment
from inventory_tracking.presentation import Tone
from pricing.knowledge.__main__ import DEFAULT_DATABASE
from pricing.knowledge.assessment.maintenance.replay import replay
from pricing.knowledge.pipeline import retrieve_draft
from tests.pricing.knowledge.assessment.item_bank.models import Item


CHARM = Item('Grand Charm', 'magic', raw_stats=((188, 40, 1), (7, 0, 37 << 8)), complete=True)


def test_saved_trainers_life_charm_has_trade_highlight_without_inventing_price():
    result = replay('trainers_grand_charm_life37')
    assert '+37' in result['text']
    assert 'Summoning Skills (Druid Only)' in result['text']
    assert 'VALUABLE CANDIDATE' in result['text']
    assert 'Druid Summoning skiller with 30-45 Life' in result['text']
    assert result['price_estimate']['estimate_ist'] is None


def test_druid_life_skiller_trade_highlight_color():
    result = retrieve_draft(CHARM.capture(), DEFAULT_DATABASE)
    document = ItemAssessment.from_record({'state': 'complete', 'request_id': 'charm', 'result': result})
    assert any(line.text == 'VALUABLE CANDIDATE' and line.tone == Tone.VALUABLE for line in document.lines)


def test_conditional_watch_does_not_leak_into_legacy_unfiltered_watchlist():
    from pricing.knowledge.index import lookup

    result = lookup(DEFAULT_DATABASE, 'Grand Charm', rarity='magic')
    assert result['evidence'].get('affixed_value_watch')
    assert not result['evidence'].get('value_watch')
