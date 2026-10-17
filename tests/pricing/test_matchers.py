from dataclasses import dataclass

from dirty_equals import Contains, IsPartialDict, IsStr

from tests.pricing.matchers import forget_comparisons


@dataclass(frozen=True)
class Case:
    expected: dict


def test_nested_matchers_forget_the_compared_result():
    inner = IsPartialDict(tier=IsStr(regex='^(high|low)$'))
    case = Case({'roles': Contains(IsPartialDict(id='a')), 'trade_tier': inner})
    result = {'roles': [{'id': 'a', 'big': list(range(100))}], 'trade_tier': {'tier': 'high', 'other': 1}}
    assert result == IsPartialDict(**case.expected)
    assert repr(inner) == repr(result['trade_tier'])  # a matched matcher shows, and so keeps, what it was compared with

    forget_comparisons({'case': case})

    assert repr(inner) == "IsPartialDict(tier=IsStr(regex='^(high|low)$'))"
    assert repr(case.expected['roles']) == "Contains(IsPartialDict(id='a'))"
    assert result == IsPartialDict(**case.expected)
    assert IsPartialDict(**case.expected) != {'roles': [], 'trade_tier': {'tier': 'high'}}


def test_plain_values_and_cycles_are_left_alone():
    looped: list = [1, 'a', None]
    looped.append(looped)
    forget_comparisons(looped)
    assert looped[:3] == [1, 'a', None]
