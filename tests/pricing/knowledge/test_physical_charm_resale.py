from dataclasses import replace
from pathlib import Path

import pytest

from inventory_tracking.appraisal.presentation import watch_tones
from inventory_tracking.appraisal.sections import value_watch_lines
from inventory_tracking.presentation import Tone
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.value_watch import matching_watches
from pricing.knowledge.valuable import build_watchlist
from tests.pricing.knowledge.assessment.item_bank.models import Item


@pytest.fixture(scope='module')
def rows():
    return build_watchlist(Path(__file__).parents[3])['rows']


@pytest.mark.parametrize(
    ('base', 'damage', 'ar', 'life', 'niche'),
    [
        ('Small Charm', 3, 20, 20, False),
        ('Large Charm', 6, 48, 35, False),
        ('Grand Charm', 10, 76, 45, False),
        ('Small Charm', 3, 20, 15, True),
    ],
)
def test_shared_group_preserves_size_conditions_and_does_not_invent_liquidity(rows, base, damage, ar, life, niche):
    item = Item(base, 'magic', raw_stats=((22, 0, damage), (19, 0, ar), (7, 0, life * 256)), complete=True)
    matched = matching_watches(rows, normalize(item.capture()))
    physical = [row for row in matched if row['details'].get('resale_group', {}).get('id') == 'physical-charm-life']
    assert len(physical) == 1
    group = physical[0]['details']['resale_group']
    assert group['liquidity'] == 'unverified'
    assert group['buyer_focus'] == ('low_level' if niche else 'physical_damage')
    report = '\n'.join(value_watch_lines({'value_watch': physical}))
    assert ('NICHE TRADE CANDIDATE' if niche else 'TRADE CANDIDATE') in report
    assert 'liquidity unverified' in report
    assert 'KEEP TO SELL' not in report
    assert 'Maximum damage + attack rating + life' in report
    heading = report.splitlines()[0]
    assert watch_tones({'value_watch': physical})[heading] == (Tone.TIER_MED if niche else Tone.TIER_LOW)
    # Missing decisive stats and ineligible bases must not satisfy the group.
    facts = normalize(item.capture())
    missing = replace(facts, stats={k: v for k, v in facts.stats.items() if k != '19:0'})
    assert not matching_watches(physical, missing)
    assert not matching_watches(physical, replace(facts, base_name='Ring'))


@pytest.mark.parametrize(
    ('watch_id', 'group_id', 'niche'),
    [
        ('shimmering-life', 'resistance-charm', False),
        ('large-shimmering-life', 'resistance-charm', False),
        ('grand-shimmering-life', 'resistance-charm', False),
        ('fire-good-luck', 'resistance-charm', False),
        ('shimmering-sustenance', 'resistance-charm', True),
        ('ruby-fervor', 'socket-jewel', False),
        ('ruby-fire-fervor', 'socket-jewel', False),
        ('scintillating-freedom', 'socket-jewel', False),
        ('rusty-carnage', 'socket-jewel', True),
        ('carbuncle-carnage', 'socket-jewel', True),
        ('shocking-life', 'elemental-charm', True),
        ('pestilent-life', 'elemental-charm', True),
        ('lucky-gold', 'gold-find-charm', True),
        ('warcries-gold', 'gold-find-charm', True),
        ('snake-sustenance', 'resource-charm', True),
        ('serpent-life', 'resource-charm', False),
        ('fine-good-luck', 'physical-charm-magic-find', False),
        ('druid-summoning-life-skiller', 'skill-charm', False),
    ],
)
def test_reviewed_collectible_groups_share_candidate_presentation(rows, watch_id, group_id, niche):
    row = next(r for r in rows if r['details'].get('watch_id') == watch_id)
    details = row['details']
    assert details['resale_group']['id'] == group_id
    assert details['resale_group']['liquidity'] == 'unverified'
    heading = value_watch_lines({'value_watch': [row]})[0]
    assert heading == ('NICHE TRADE CANDIDATE' if niche else 'TRADE CANDIDATE') + ' — liquidity unverified'
    assert watch_tones({'value_watch': [row]})[heading] == (Tone.TIER_MED if niche else Tone.TIER_LOW)


def test_overlapping_charm_uses_are_order_independent_and_niche_use_does_not_hide_another_buyer(rows):
    item = Item('Small Charm', 'magic', raw_stats=(*((s, 0, 5) for s in (39, 41, 43, 45)), (79, 0, 10)), complete=True)
    matched = matching_watches(rows, normalize(item.capture()))
    assert len(matched) == 3  # Resistance, resistance/gold-find, plain gold-find.
    lines = value_watch_lines({'value_watch': matched})
    assert lines == value_watch_lines({'value_watch': list(reversed(matched))})
    assert lines[0] == 'TRADE CANDIDATE — liquidity unverified'
    assert sum('TRADE CANDIDATE' in line for line in lines) == 1
    assert any('All resistances: 5' in line for line in lines)
    assert any('Niche: All resistances + gold find' in line for line in lines)
    assert watch_tones({'value_watch': matched}) == watch_tones({'value_watch': list(reversed(matched))})
    assert watch_tones({'value_watch': matched})[lines[0]] == Tone.TIER_LOW
