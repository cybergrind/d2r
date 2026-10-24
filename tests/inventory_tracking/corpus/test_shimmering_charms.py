"""Shimmering charms (magic charms with the all-resistances prefix) are kept and priced by what they sold for.

The player, 2026-10-24: "add shimmering charms into corpus: tests + definitive valuation based on real deals (not just
ask) / I want to make sure that we keep them". The corpus holds the real captures (data/pinned.json, from the mule
collection); the roll variants below are those reads with their rolls changed. Each runs the loop's own path: the
identify worker's triage (pricing.api fast_triage, its tables and pricing/data/charm-evidence.json), then the one
assessment entry point (loot/assess.py) at the card, the town and the field.
"""

import copy
import json
from typing import Any

import pytest

from inventory_tracking.corpus.build import DATA
from inventory_tracking.identify.service import card_of
from inventory_tracking.items.metadata import metadata
from inventory_tracking.loot.assess import Assessor, CalledCopies, Outcome, ResultAppraiser, Site
from inventory_tracking.loot.facts import Owner, Where, from_observation
from inventory_tracking.loot.value import DUPLICATE_IST
from pricing.api import fast_triage


PINNED = json.loads((DATA / 'pinned.json').read_text())
SHIMMERING = {key: row['observation'] for key, row in PINNED.items() if row['why'].startswith('shimmering charm')}
RESISTS = (39, 41, 43, 45)
VITA_5_20, GOOD_LUCK_5_7 = 'dca066508114', 'c1122216c534'  # the real Small Charms: 5 all res + 20 life / + 7% MF
NO_COPIES = CalledCopies(lambda _facts: [])


def judged(observation: dict[str, Any], site: Site = Site.CARD):
    result = fast_triage(observation)
    assert result is not None, 'the identify worker routes magic charms to the triage'
    facts = from_observation(observation, where=Where.INVENTORY, owner=Owner.LOOP)
    return result['triage'], Assessor(ResultAppraiser(lambda _: result), NO_COPIES).assess(facts, site)


def variant(res: int, companion: tuple[int, int] | None) -> dict[str, Any]:
    """The real Good Luck read with `res` all resistances and `companion` (stat id, shown value) as its suffix."""
    observation = copy.deepcopy(SHIMMERING[GOOD_LUCK_5_7])
    item = observation['item']
    item['affixes'] = [a for a in item['affixes'] if a['memory_stat']['id'] in RESISTS]
    observation['decoded_stats'] = [s for s in observation['decoded_stats'] if s['memory_stat']['id'] in RESISTS]
    for row in (*item['affixes'], *observation['decoded_stats']):
        row['value'] = row['memory_stat']['raw'] = res
    observation['source']['native_affixes']['suffix'] = []
    if companion is not None:
        stat, value = companion
        about = metadata()['stats'][str(stat)]
        raw = value * 256 if stat == 7 else value  # maxhp is kept in 256ths
        memory = {'id': stat, 'layer': 0, 'raw': raw}
        item['affixes'].append({'descriptor_offset': 232, 'label': about['label'], 'memory_stat': memory,
                                'property_id': about['property_id'], 'value': value})  # fmt: skip
        text = about['label'].replace('{{value}}', str(value))
        observation['decoded_stats'].append({'memory_stat': memory, 'status': 'decoded', 'name': about['name'],
                                             'value': value, 'text': text})  # fmt: skip
    return observation


@pytest.mark.parametrize('key', sorted(SHIMMERING))
def test_every_pinned_shimmering_charm_is_kept_at_the_card_the_town_and_the_field(key):
    for site in (Site.CARD, Site.TOWN, Site.FIELD):
        _, assessment = judged(SHIMMERING[key], site)
        assert assessment.outcome == Outcome.KEEP, (site, assessment.said())


@pytest.mark.parametrize('key', [VITA_5_20, GOOD_LUCK_5_7])
def test_the_real_shimmering_small_charms_are_priced_by_completed_trades_and_count_as_expensive(key):
    triage, assessment = judged(SHIMMERING[key])
    assert triage['band']['evidence_kind'] == 'fills', triage['reason']
    assert triage['band']['fills'] >= 3
    assert triage['verdict'] in ('sell', 'slow')
    assert assessment.value is not None
    assert assessment.value.worth_ist is not None
    assert assessment.value.worth_ist >= DUPLICATE_IST


def test_card_of_says_keep_for_the_perfect_vita():
    observation = SHIMMERING[VITA_5_20]
    found = card_of(observation, fast_triage(observation), copies=NO_COPIES)
    assert found is not None
    assert found['outcome'] == 'keep'


COMPANIONS = [None, (7, 16), (7, 20), (80, 6), (80, 7), (96, 3), (99, 5), (2, 2)]


@pytest.mark.parametrize('res', [3, 4, 5])
@pytest.mark.parametrize('companion', COMPANIONS, ids=lambda c: 'plain' if c is None else f'{c[0]}={c[1]}')
def test_every_shimmering_small_charm_roll_is_kept_by_its_always_kept_row(res, companion):
    observation = variant(res, companion)
    for site in (Site.CARD, Site.TOWN):
        _, assessment = judged(observation, site)
        assert assessment.outcome == Outcome.KEEP, (site, assessment.said())
        assert assessment.value is not None
        assert any(want.always_keep and want.id == 'shimmering-small-charm' for want in assessment.value.wants)
