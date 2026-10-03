"""Retain each decoded drop before valuation, including lookup failures and vendor items."""

from uuid import uuid4

from inventory_tracking.corpus.build import item_id
from inventory_tracking.reports import publish


def persist(directory, observation):
    path = directory / 'identified' / f'{uuid4().hex}.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    publish(path, {'id': item_id(observation), 'observation': observation})
    return path
