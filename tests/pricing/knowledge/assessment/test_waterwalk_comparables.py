"""Waterwalk defense proof preserves quantity, scope and price-dispersion gates."""

import json
from copy import deepcopy
from datetime import date
from functools import lru_cache
from pathlib import Path

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables
from pricing.knowledge.assessment.handlers.named import NamedHandler
from tests.pricing.knowledge.assessment.item_bank.models import Item


@lru_cache
def listings():
    return [
        r
        for r in map(json.loads, Path('pricing/data/appraisal-market.jsonl').read_text().splitlines())
        if r.get('name') == 'Waterwalk'
    ]


def contract(base, defense):
    item = Item(
        base,
        'unique',
        'Waterwalk',
        (
            (31, 0, defense),
            (16, 0, 210),
            (32, 0, 100),
            (96, 0, 20),
            (2, 0, 15),
            (7, 0, 65 * 256),
            (11, 0, 40 * 256),
            (40, 0, 5),
            (28, 0, 50),
        ),
        complete=True,
    )
    result, gaps = NamedHandler().contract(normalize(item.capture()), 'accessory')
    assert result is not None, gaps
    return result.to_dict()


def test_cached_upgraded_cohort_is_recognized_but_dispersion_prevents_price():
    rows = listings()
    before = deepcopy(rows)
    compared = evaluate(contract('Scarabshell Boots', 198), rows)
    assert {r['id'] for r in compared['accepted']} == {
        '345f52cb294a0b1a0990d487',
        'd1c6bb74815bdb8a2cbb05ad',
        '28e59ed909b6fad2d7d79724',
    }
    price = price_from_comparables(compared, today=date(2026, 10, 2))
    assert price['sellers'] == 3
    assert price['estimate_ist'] is None
    assert price['unavailable_reason'] == 'dispersed'
    assert rows == before


def test_other_upgraded_defense_rolls_are_not_pooled():
    compared = evaluate(contract('Scarabshell Boots', 201), listings())
    assert not compared['accepted']


def test_original_variant_proof_does_not_repair_ambiguous_units():
    ids = {'bf140fe61fd30ef44e624aa1', '0dbce0847b481b760c0ce327'}
    rows = [r for r in listings() if r['id'] in ids]
    assert len(rows) == 2
    compared = evaluate(contract('Sharkskin Boots', 124), rows)
    assert not compared['accepted']
    assert all('Ambiguous unit, missing seller or invalid price.' in r['reasons'] for r in compared['rejected'])
