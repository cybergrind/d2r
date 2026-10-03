from dataclasses import replace
from datetime import date

import pytest

from inventory_tracking.appraisal.presentation import ItemAssessment
from inventory_tracking.presentation import Tone
from pricing.knowledge.__main__ import DEFAULT_DATABASE
from pricing.knowledge.pipeline import retrieve_draft
from tests.pricing.knowledge.assessment.item_bank.cases.tribrid_raven import FIXED, ITEM


@pytest.mark.parametrize(
    ('dex', 'ar', 'status', 'label'),
    [
        (15, 150, 'candidate', 'ordinary'),
        (19, 250, 'candidate', 'ordinary'),
        (20, 249, 'candidate', 'ordinary'),
        (20, 250, 'premium', 'premium'),
    ],
)
def test_native_raven_trade_assessment_reaches_report_without_loadout(dex, ar, status, label):
    item = replace(ITEM, raw_stats=(*FIXED, (2, 0, dex), (19, 0, ar)))
    result = retrieve_draft(item.capture(), DEFAULT_DATABASE, as_of=date(2026, 10, 1))
    assert result['assessment']['trade_qualification']['status'] == status
    document = ItemAssessment.from_record({'state': 'complete', 'request_id': 'raven-trade', 'result': result})
    lines = [line for line in document.lines if line.text.startswith('Trade:')]
    assert len(lines) == 1
    assert lines[0].text.startswith(f'Trade: {label} candidate')
    assert lines[0].tone == (Tone.TIER_HIGH if status == 'premium' else Tone.TIER_LOW)
    assert 'Trade tier:' in document.to_text()
    assert '20 dexterity' in lines[0].text
    assert '250 attack rating' in lines[0].text


def test_missing_decisive_roll_does_not_render_trade_candidate():
    result = retrieve_draft(
        replace(ITEM, raw_stats=(*FIXED, (19, 0, 250))).capture(), DEFAULT_DATABASE, as_of=date(2026, 10, 1)
    )
    assert result['assessment']['trade_qualification']['status'] == 'unresolved'
    document = ItemAssessment.from_record({'state': 'complete', 'request_id': 'raven-trade', 'result': result})
    assert not any(line.text.startswith('Trade:') for line in document.lines)


@pytest.mark.parametrize(
    ('name', 'base', 'rarity', 'tone'),
    [
        ('The Stone of Jordan', 'Ring', 'unique', Tone.TIER_HIGH),
        ("Tal Rasha's Adjudication", 'Amulet', 'set', Tone.TIER_LOW),
    ],
)
def test_fixed_jewelry_report_has_no_artificial_ordinary_or_perfect_roll_grade(name, base, rarity, tone):
    from tests.pricing.knowledge.assessment.item_bank.models import Item

    result = retrieve_draft(Item(base, rarity, name).capture(), DEFAULT_DATABASE, as_of=date(2026, 10, 1))
    document = ItemAssessment.from_record({'state': 'complete', 'request_id': 'fixed-trade', 'result': result})
    lines = [line for line in document.lines if line.text.startswith('Trade:')]
    assert len(lines) == 1
    assert lines[0].text.startswith('Trade: candidate —')
    assert lines[0].tone == tone
    assert 'fixed' in lines[0].text.lower()
    assert 'Trade: ordinary' not in document.to_text()
    assert 'Trade: premium' not in document.to_text()
