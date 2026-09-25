"""Socket occupancy: a partial child list never proves empty slots."""

from dataclasses import dataclass

from pricing.knowledge.assessment.domain.facts import Fact, FactStatus


@dataclass(frozen=True)
class SocketState:
    total: Fact[int]
    occupied: Fact[int]
    empty: Fact[int]
    identities_complete: bool


def valid(n):
    return type(n) is int and 0 <= n <= 6


def socket_state(total, contents, items, occupied=None, empty=None):
    known = FactStatus.KNOWN
    unknown = FactStatus.UNKNOWN
    conflict = FactStatus.CONFLICTING
    invalid = (
        (total is not None and not valid(total))
        or (occupied is not None and not valid(occupied))
        or (empty is not None and not valid(empty))
    )
    if valid(total):
        invalid |= len(items) > total
        invalid |= contents == 'empty' and bool(items)
        invalid |= contents == 'filled' and total == 0
        if valid(occupied) and valid(empty):
            invalid |= occupied + empty != total
        if valid(occupied):
            invalid |= occupied > total or len(items) > occupied
        if valid(empty):
            invalid |= empty > total
    if invalid:
        return SocketState(Fact(total, conflict), Fact(occupied, conflict), Fact(empty, conflict), False)
    if valid(total) and contents == 'empty':
        if occupied not in (None, 0) or empty not in (None, total):
            return SocketState(Fact(total, conflict), Fact(occupied, conflict), Fact(empty, conflict), False)
        occupied, empty = 0, total
    elif valid(total) and valid(occupied):
        empty = total - occupied
    elif valid(total) and valid(empty):
        occupied = total - empty
    elif valid(total) and len(items) == total and total > 0:
        occupied, empty = total, 0
    return SocketState(
        Fact(total, known if valid(total) else unknown),
        Fact(occupied, known if valid(occupied) else unknown),
        Fact(empty, known if valid(empty) else unknown),
        valid(occupied) and len(items) == occupied and all(i.get('name') for i in items),
    )
