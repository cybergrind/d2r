"""Small validated predicate language with explicit unknown-state propagation."""

import math
from dataclasses import asdict, dataclass
from enum import StrEnum

from pricing.knowledge.assessment.domain.context import CONTEXT_FIELDS, NUMERIC_CONTEXT_FIELDS, AssessmentContext
from pricing.knowledge.assessment.domain.facts import Fact, FactStatus, StatKey
from pricing.knowledge.assessment.roles.charges import charge_availability
from pricing.knowledge.assessment.roles.socket_payload import jewel_matches, jewel_stat, runes_equal


class Truth(StrEnum):
    TRUE = 'true'
    FALSE = 'false'
    UNKNOWN = 'unknown'
    NOT_APPLICABLE = 'not_applicable'


FACT_FIELDS = frozenset(
    {'name', 'base_code', 'item_type', 'rarity', 'runeword', 'identified', 'ethereal', 'sockets', 'socket_contents'}
)
STAT_UNITS = frozenset({'replenishment_rate', 'percent_chance'})


@dataclass(frozen=True)
class PredicateResult:
    truth: Truth
    reason: str
    observed: object = None
    expected: object = None
    children: tuple = ()

    def to_dict(self):
        return asdict(self)


def validate(rule):
    if not isinstance(rule, dict):
        raise ValueError('Predicate must be an object')
    for group in ('all', 'any', 'not'):
        if group in rule:
            if set(rule) != {group}:
                raise ValueError('Compound predicate has extra fields')
            children = [rule[group]] if group == 'not' else rule[group]
            if not isinstance(children, list) or not children:
                raise ValueError('Predicate group must be nonempty')
            for child in children:
                validate(child)
            return
    op = rule.get('op')
    if op == 'socket_runes_equal':
        from inventory_tracking.items.metadata import metadata

        names = rule.get('value')
        known = {b['name'] for b in metadata()['bases'].values() if b['type'] == 'rune'}
        if (
            set(rule) != {'op', 'value'}
            or not isinstance(names, list)
            or not 1 <= len(names) <= 6
            or any(not isinstance(name, str) or name not in known for name in names)
        ):
            raise ValueError('Invalid exact rune payload predicate')
    elif op == 'socket_jewel_matches':
        if set(rule) - {'name'} != {'op', 'stats'} or not isinstance(rule['stats'], dict) or not rule['stats']:
            raise ValueError('Invalid compound socket jewel predicate')
        if 'name' in rule and (not isinstance(rule['name'], str) or not rule['name'].strip()):
            raise ValueError('Socket jewel name must be nonempty')
        for key, value in rule['stats'].items():
            validate({'op': 'stat_at_least', 'key': key, 'value': value})
    elif op == 'socket_jewel_stat_at_least':
        if set(rule) != {'op', 'key', 'value'}:
            raise ValueError('Invalid socket jewel predicate')
        validate({**rule, 'op': 'stat_at_least'})
    elif op == 'stat_at_least':
        if (
            set(rule) - {'absent_is_zero', 'unit'} != {'op', 'key', 'value'}
            or type(rule.get('absent_is_zero', False)) is not bool
        ):
            raise ValueError('Invalid stat predicate fields')
        if 'unit' in rule and (type(rule['unit']) is not str or rule['unit'] not in STAT_UNITS):
            raise ValueError('Invalid stat predicate unit')
        try:
            stat, parameter = rule['key'].split(':')
            if int(stat) < 0 or int(parameter) < 0:
                raise ValueError
        except (ValueError, TypeError, AttributeError) as error:
            raise ValueError('Invalid native stat key') from error
        value = rule['value']
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError('Stat threshold must be finite numeric')
    elif op == 'context_at_least':
        if (
            set(rule) != {'op', 'field', 'value'}
            or rule['field'] not in NUMERIC_CONTEXT_FIELDS
            or type(rule['value']) is not int
            or rule['value'] < 0
        ):
            raise ValueError('Invalid numeric context threshold')
    elif op == 'context_count_at_least':
        if (
            set(rule) != {'op', 'field', 'value', 'count'}
            or rule['field'] not in ('player_items', 'mercenary_items')
            or type(rule['value']) is not str
            or not rule['value'].strip()
            or type(rule['count']) is not int
            or rule['count'] < 1
        ):
            raise ValueError('Invalid item count predicate')
    elif op == 'charge_skill':
        if (
            set(rule) != {'op', 'skill_id', 'value'}
            or any(type(rule[k]) is not int for k in ('skill_id', 'value'))
            or not 0 <= rule['skill_id'] <= 4095
            or not 0 <= rule['value'] <= 255
        ):
            raise ValueError('Invalid charge skill predicate')
    elif op in ('fact_eq', 'context_eq', 'context_contains'):
        allowed = FACT_FIELDS if op == 'fact_eq' else CONTEXT_FIELDS
        if set(rule) != {'op', 'field', 'value'} or rule['field'] not in allowed:
            raise ValueError('Invalid fact/context predicate')
        field = rule['field']
        if op == 'context_contains':
            if field not in ('player_items', 'mercenary_items'):
                raise ValueError('Membership requires a collection context field')
            expected_type = str
        elif field in ('player_items', 'mercenary_items'):
            raise ValueError('Use membership for collection context fields')
        else:
            expected_type = (
                bool
                if field in ('ethereal', 'identified')
                else int
                if field == 'sockets' or field in NUMERIC_CONTEXT_FIELDS
                else str
            )
        if type(rule['value']) is not expected_type:
            raise ValueError('Predicate value type disagrees with field type')
        if expected_type is int and rule['value'] < 0:
            raise ValueError('Predicate integer type requires nonnegative value')
    else:
        raise ValueError(f'Unknown predicate operation: {op}')


def combine(group, children):
    values = {child.truth for child in children}
    if group == 'not':
        return {Truth.TRUE: Truth.FALSE, Truth.FALSE: Truth.TRUE}.get(children[0].truth, children[0].truth)
    dominant, remainder = (Truth.FALSE, Truth.TRUE) if group == 'all' else (Truth.TRUE, Truth.FALSE)
    if dominant in values:
        return dominant
    if Truth.UNKNOWN in values:
        return Truth.UNKNOWN
    return remainder if remainder in values else Truth.NOT_APPLICABLE


def evaluate(rule, facts, context=None):
    validate(rule)
    return _evaluate(rule, facts, AssessmentContext.from_input(context))


def _evaluate(rule, facts, context):
    for group in ('all', 'any', 'not'):
        if group in rule:
            nodes = [rule[group]] if group == 'not' else rule[group]
            children = tuple(_evaluate(node, facts, context) for node in nodes)
            return PredicateResult(combine(group, children), group, children=children)
    op = rule['op']
    if op == 'socket_runes_equal':
        truth, observed = runes_equal(facts, rule['value'])
        return PredicateResult(Truth(truth), 'Exact linked socket rune contents', observed, rule['value'])
    if op == 'socket_jewel_matches':
        truth, observed = jewel_matches(facts, rule['stats'], name=rule.get('name'))
        return PredicateResult(Truth(truth), 'One socket jewel matches all required stats', observed, rule['stats'])
    expected = rule['value']
    if op == 'context_at_least':
        fact = context.fact(rule['field'])
        label = f'{rule["field"]} >= {expected}'
        if fact.status != FactStatus.KNOWN:
            return PredicateResult(Truth.UNKNOWN, label, expected=expected)
        return PredicateResult(Truth.TRUE if fact.value >= expected else Truth.FALSE, label, fact.value, expected)
    if op == 'socket_jewel_stat_at_least':
        truth, observed = jewel_stat(facts, rule['key'], expected)
        return PredicateResult(Truth(truth), f'Socket jewel {rule["key"]} >= {expected}', observed, expected)
    if op == 'context_count_at_least':
        items = context.fact(rule['field'])
        count = rule['count']
        label = f'{rule["field"]}: at least {count} copies of {expected}'
        target = {'item': expected, 'count': count}
        if items.status != FactStatus.KNOWN:
            return PredicateResult(Truth.UNKNOWN, label, expected=target)
        if isinstance(items.value, frozenset) and expected in items.value and count > 1:
            return PredicateResult(Truth.UNKNOWN, label, expected=target)
        observed = sum(item == expected for item in items.value)
        return PredicateResult(Truth.TRUE if observed >= count else Truth.FALSE, label, observed, target)
    if op == 'charge_skill':
        truth, observed = charge_availability(facts, rule['skill_id'], expected)
        return PredicateResult(
            Truth(truth), f'Charged skill {rule["skill_id"]}: at least {expected} remaining', observed, expected
        )
    if op == 'stat_at_least':
        if 'unit' in rule and facts.stats.get(rule['key'], {}).get('unit') != rule['unit']:
            return PredicateResult(
                Truth.UNKNOWN, f'Native stat {rule["key"]} requires unit {rule["unit"]}', expected=expected
            )
        fact = facts.stat(StatKey(*map(int, rule['key'].split(':'))))
        if rule.get('absent_is_zero') and rule['key'] not in facts.stats and facts.capture_complete and not facts.gaps:
            fact = Fact(0, FactStatus.KNOWN, 'complete_stat_inventory')
        label = f'Native stat {rule["key"]} >= {expected}'
        if fact.status != FactStatus.KNOWN or type(fact.value) not in (int, float) or not math.isfinite(fact.value):
            return PredicateResult(Truth.UNKNOWN, label, expected=expected)
        success = fact.value >= expected
        observed = fact.value
    else:
        field = rule['field']
        label = f'{field}: {expected}'
        if op == 'fact_eq':
            fact = facts.fact(field)
            if fact.status != FactStatus.KNOWN:
                return PredicateResult(Truth.UNKNOWN, label, expected=expected)
            observed = fact.value
        else:
            if context.fact(field).status != FactStatus.KNOWN:
                return PredicateResult(Truth.UNKNOWN, label, expected=expected)
            observed = context.fact(field).value
        if op == 'context_contains':
            if not isinstance(observed, (list, tuple, set, frozenset)):
                return PredicateResult(Truth.UNKNOWN, label, expected=expected)
            success = expected in observed
            observed = sorted(observed)
        else:
            success = type(observed) is type(expected) and observed == expected
    return PredicateResult(Truth.TRUE if success else Truth.FALSE, label, observed, expected)


def native_keys(rule):
    """Native keys needing catalog validation during rule publication."""
    if rule.get('op') == 'socket_jewel_matches':
        yield from rule['stats']
    if rule.get('op') in ('stat_at_least', 'socket_jewel_stat_at_least'):
        yield rule['key']
    if rule.get('op') == 'charge_skill':
        yield f'204:{rule["skill_id"] * 64 + 1}'
    for group in ('all', 'any', 'not'):
        if group in rule:
            for node in [rule[group]] if group == 'not' else rule[group]:
                yield from native_keys(node)
