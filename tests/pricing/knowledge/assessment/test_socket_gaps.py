from dataclasses import replace

import pytest

from pricing.knowledge.assessment.handlers.exact import BaseHandler
from pricing.knowledge.assessment.handlers.named import NamedHandler
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize('named', [False, True])
def test_unknown_contents_are_not_reported_as_filled_or_duplicated(named):
    item = facts('Long Sword', 'unique', 'Hellplague') if named else facts('Crystal Sword')
    handler = NamedHandler() if named else BaseHandler()
    for gaps in ([], ['socket_contents is unknown or unverified.']):
        contract, reasons = handler.contract(replace(item, socket_contents=None, gaps=gaps), 'weapon')
        assert contract is None
        socket_reasons = [r for r in reasons if 'socket' in r.lower()]
        assert len(socket_reasons) == 1
        assert 'filled' not in socket_reasons[0].lower()


@pytest.mark.parametrize('named', [False, True])
def test_filled_contents_keep_contribution_comparison_requirement(named):
    item = facts('Long Sword', 'unique', 'Hellplague') if named else facts('Crystal Sword')
    handler = NamedHandler() if named else BaseHandler()
    contract, reasons = handler.contract(replace(item, sockets=1, socket_contents='filled'), 'weapon')
    assert contract is None
    assert any('Filled' in r and 'contribution' in r for r in reasons)
