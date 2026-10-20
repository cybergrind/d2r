"""Shadow mode of the loot design (loot/design.md §7 M1): the new decisions logged beside the old ones, nothing done.

Two hooks, one call each: the town visit (macros/visit.py, where the loop has judged its items: identify, copies,
junk) calls `town`, and the ground look (macros/pickmode.py `kept`) calls `ground`. Each logs one line per item
(once per item and decision, not at every look) and a town summary:

    Macro: loot: shadow: Goblin Toe (Light Plated Boots): new drop K6 cheap (0.647 Ist), not better than the 2
        owned: stat 16:0 50 vs 53, 56 / old keep slow (differ)
    Macro: loot: shadow: town: 9 items, 1 differ (new gives up 1 the old keeps, new keeps 0 the old sells)
    Macro: loot: shadow: ground: magic Monarch: new pick G6 identify / old leave (differ)

While the town's one decision is off (loot/keep.py TOWN_DECIDES, M6), the town hook also logs what it would sell,
one line per item where it differs from the visit's sale, and a summary per visit:

    Macro: loot: shadow: town merge: magic Sash: would sell: K8 worthless (...), no want / old keep (differ)
    Macro: loot: shadow: town merge: 9 items, would sell 2, 1 differ (sells 1 the old keeps, keeps 0 the old sells)

The values come from the identify worker's KB results, noted here as the worker makes them (`note`, called by
identify/service.py; the same process). Owned copies are read from the collection (value.py `CollectionCopies`,
read-only). Nothing here changes what the loop picks, sells, drops or stashes, and nothing raises into the visit or
the look: an error is logged once per kind and the shadow goes on. `keep.SHADOW = False` turns it off.
"""

import threading
from collections import OrderedDict
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from inventory_tracking.common import LOG
from inventory_tracking.game.records import VALUABLE, Carried, Drop, Loot
from inventory_tracking.loot import ground_judge, keep
from inventory_tracking.loot.facts import Owner, from_carried, from_drop
from inventory_tracking.loot.keep import Action, decide_all
from inventory_tracking.loot.value import CollectionCopies, OwnedCopies, appraise_result, assess


__all__ = ['BOOK', 'SHADOW', 'Appraised', 'Book', 'Shadow', 'ground', 'note', 'town']

PREFIX = 'Macro: loot: shadow:'
SEEN_MOST = 4000  # ground items remembered at most (a game shows far fewer)


@dataclass(frozen=True)
class Appraised:
    """An identify worker's appraisal of a unit: its read, the KB result and the verdict it gave."""

    observation: Mapping[str, Any]
    result: Mapping[str, Any]
    verdict: str | None


class Book:
    """The last appraisals by unit id, bounded; written by the identify worker's threads, read by the runner's."""

    MOST = 512

    def __init__(self) -> None:
        self.found: OrderedDict[int, Appraised] = OrderedDict()
        self.lock = threading.Lock()

    def put(self, unit: int, appraised: Appraised) -> None:
        with self.lock:
            self.found[unit] = appraised
            self.found.move_to_end(unit)
            while len(self.found) > self.MOST:
                self.found.popitem(last=False)

    def get(self, unit: int) -> Appraised | None:
        with self.lock:
            return self.found.get(unit)


BOOK = Book()


def note(observation: Mapping[str, Any], result: Mapping[str, Any] | None, row: Mapping[str, Any]) -> None:
    """Keep an appraisal for the shadow (identify/service.py, after each item's summary). Never raises."""
    if result is None:
        return
    try:
        BOOK.put(int(row['unit_id']), Appraised(observation, result, row.get('verdict')))
    except Exception:  # never into the identify worker
        return


class Shadow:
    """What the shadow said already (per game on the ground, per item and decision in town) and its failures."""

    def __init__(self, book: Book = BOOK, log: Callable[..., None] = LOG.info) -> None:
        self.book, self.log = book, log
        self.game: tuple[str, int] | None = None
        self.ground_seen: set[tuple[int, int, bool]] = set()
        self.town_seen: set[tuple[int, str, str, bool]] = set()
        self.failed: set[str] = set()

    def _failed(self, where: str, error: Exception) -> None:
        kind = f'{where}:{type(error).__name__}'
        if kind in self.failed:
            return
        self.failed.add(kind)
        with suppress(Exception):  # the log itself failing must not stop the loop either
            self.log('%s %s failed (%s: %s); the %s goes on', PREFIX, where, type(error).__name__, error,
                     'visit' if where == 'town' else 'look')  # fmt: skip

    def town(
        self,
        carried: Sequence[Carried],
        junk: frozenset[int],
        spared: frozenset[int] = frozenset(),
        copies: OwnedCopies | None = None,
        stacked: frozenset[int] = frozenset(),
    ) -> list[str]:
        """The new decisions on the loop's carried items (`carried`: inventory and cube) beside the visit's
        (`junk`: the unit ids it sells; `spared`: the player's by its stats; `stacked`: the full stacks' materials,
        sold by both). Returns the lines logged."""
        if not keep.SHADOW:
            return []
        copies = copies or CollectionCopies()
        try:
            lines = self._town(carried, junk, spared, copies)
        except Exception as error:  # never into the visit
            self._failed('town', error)
            return []
        if keep.TOWN_DECIDES:
            return lines  # the visit's sale is the merged decision itself
        try:
            return [*lines, *self._merge(carried, junk, spared, copies, stacked)]
        except Exception as error:  # never into the visit
            self._failed('town merge', error)
            return lines

    def _merge(self, carried: Sequence[Carried], junk: frozenset[int], spared: frozenset[int], copies: OwnedCopies,
               stacked: frozenset[int]) -> list[str]:  # fmt: skip
        """M6's town decision (loot/api.py `town_verdicts`) beside the visit's sale: a line per item that differs."""
        from inventory_tracking.loot.api import town_verdicts  # the api imports this module

        items = []
        for item in carried:
            entry = self.book.get(item.unit_id)
            owner = Owner.PLAYER if item.unit_id in spared else Owner.LOOP
            facts = from_carried(item, owner=owner, observation=entry.observation if entry is not None else None)
            items.append((facts, appraise_result(facts, entry.result, entry.verdict) if entry is not None else None))
        lines, selling, sells, keeps = [], 0, 0, 0
        for verdict in town_verdicts(items, copies.copies):
            unit = verdict.facts.unit_id
            sold, old = verdict.sold or unit in stacked - spared, unit in junk
            selling += sold
            if sold == old:
                continue
            sells, keeps = sells + sold, keeps + (not sold)
            line = (f'{PREFIX} town merge: {verdict.facts.title()}: would {verdict.said()} / old '
                    f'{"sell" if old else "keep"} (differ)')  # fmt: skip
            lines.append(line)
            self.log('%s', line)
        summary = (f'{PREFIX} town merge: {len(items)} items, would sell {selling}, {sells + keeps} differ (sells '
                   f'{sells} the old keeps, keeps {keeps} the old sells)')  # fmt: skip
        self.log('%s', summary)
        return [*lines, summary]

    def _town(self, carried: Sequence[Carried], junk: frozenset[int], spared: frozenset[int],
              copies: OwnedCopies) -> list[str]:  # fmt: skip
        items = []
        for item in carried:
            entry = self.book.get(item.unit_id)
            owner = Owner.PLAYER if item.unit_id in spared else Owner.LOOP
            facts = from_carried(item, owner=owner, observation=entry.observation if entry is not None else None)
            value = (
                appraise_result(facts, entry.result, entry.verdict) if entry is not None
                else assess(facts, worth=None, verdict=None)
            )  # fmt: skip
            items.append((facts, value))
        lines, differ, gives, keeps = [], 0, 0, 0
        for facts, _, decision in decide_all(items, copies.copies):
            sold = facts.unit_id in junk
            entry = self.book.get(facts.unit_id)
            verdict = f' {entry.verdict}' if entry is not None and entry.verdict else ''
            old = f'old {"sell" if sold else "keep"}{verdict}' + (' (protected)' if facts.unit_id in spared else '')
            differs = decision.action != Action.IDENTIFY and decision.gives_up != sold
            differ += differs
            gives += differs and decision.gives_up
            keeps += differs and not decision.gives_up
            key = (facts.unit_id, decision.action.value, decision.rule, sold)
            if key in self.town_seen:
                continue
            self.town_seen.add(key)
            line = f'{PREFIX} {facts.title()}: new {decision.said()} / {old}{" (differ)" if differs else ""}'
            lines.append(line)
            self.log('%s', line)
        if len(self.town_seen) > SEEN_MOST:
            self.town_seen.clear()
        summary = (f'{PREFIX} town: {len(items)} items, {differ} differ (new gives up {gives} the old keeps, '
                   f'new keeps {keeps} the old sells)')  # fmt: skip
        self.log('%s', summary)
        return [*lines, summary]

    def ground(self, loot: Loot, taken: Callable[[Drop], bool]) -> list[str]:
        """The new ground verdict on each valuable drop of a look beside today's (`taken`: whether the pickup level
        takes it), once per item and game (again once its rolls are read). Returns the lines logged."""
        if not keep.SHADOW:
            return []
        try:
            return self._ground(loot, taken)
        except Exception as error:  # never into the look
            self._failed('ground', error)
            return []

    def _ground(self, loot: Loot, taken: Callable[[Drop], bool]) -> list[str]:
        if loot.game is not None and loot.game != self.game:
            self.game = loot.game
            self.ground_seen.clear()
        if len(self.ground_seen) > SEEN_MOST:
            self.ground_seen.clear()
        lines = []
        for drop in loot.drops:
            key = (drop.unit_id, drop.txt, drop.rolls is not None)
            if drop.kind != VALUABLE or key in self.ground_seen:
                continue
            self.ground_seen.add(key)
            facts = from_drop(drop)
            new, old = ground_judge.judge(facts), taken(drop)
            differs = ' (differ)' if new.pick != old else ''
            line = f'{PREFIX} ground: {facts.title()}: new {new.said()} / old {"pick" if old else "leave"}{differs}'
            lines.append(line)
            self.log('%s', line)
        return lines


SHADOW = Shadow()


def town(
    carried: Sequence[Carried],
    junk: frozenset[int],
    spared: frozenset[int] = frozenset(),
    stacked: frozenset[int] = frozenset(),
) -> list[str]:
    """The town visit's hook (macros/visit.py `visit`): `Shadow.town` on the service's shadow."""
    return SHADOW.town(carried, junk, spared, stacked=stacked)


def ground(loot: Loot, taken: Callable[[Drop], bool]) -> list[str]:
    """The ground look's hook (macros/pickmode.py `kept`): `Shadow.ground` on the service's shadow."""
    return SHADOW.ground(loot, taken)
