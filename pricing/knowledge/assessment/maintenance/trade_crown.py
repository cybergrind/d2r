"""Source-bound Crown shell review; a baseline tier cannot certify trade coverage."""

import json

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.maintenance.trade_review_cases import REQUIRED
from pricing.knowledge.assessment.policies import crown_trade


IDENTITY = ('unique', 'Crown of Ages')
VARIANTS = REQUIRED | {
    (True, False, 2, 'empty'),
    (True, False, 2, 'filled'),
    (True, False, 2, 'unknown'),
    (True, False, 2, None),
    (True, False, 3, 'empty'),
    (True, None, 2, 'empty'),
    (True, True, 2, 'empty'),
    (False, False, 2, 'empty'),
}
PROPERTIES = (
    ('balance2', 30, 30),
    ('res-all', 20, 30),
    ('allskills', 1, 1),
    ('ac', 100, 150),
    ('indestruct', 1, 1),
    ('red-dmg%', 10, 15),
    ('ac%', 50, 50),
    ('sock', 1, 2),
)
BOUNDS = {31: (349, 399), 36: (10, 15), **dict.fromkeys((39, 41, 43, 45), (20, 30))}


def bind_policy(policy):
    validated = crown_trade.reviewed_date()
    return {
        **policy,
        'crown_trade': json.loads(read_artifact(crown_trade.RULES)),
        'crown_trade_validated_at': validated,
    }


def specification(policy, variants, stat_specs):
    if len(variants) != 1:
        return None
    definition = variants[0]
    base, game = definition.get('base_definition', {}), definition.get('game_definition', {})
    rule = policy.get('crown_trade', {})
    if (
        (policy.get('quality'), policy.get('name')) != IDENTITY
        or (definition.get('rarity'), definition.get('name')) != IDENTITY
        or definition.get('base_name') != 'Corona'
        or list(definition.get('base_codes', ())) != ['urn']
        or any(base.get(k) != v for k, v in {'code': 'urn', 'minac': 111, 'maxac': 165, 'gemsockets': 3}.items())
        or game.get('code') != 'urn'
        or {k for k in game if k.startswith('prop')} != {f'prop{i}' for i in range(1, 9)}
        or any(
            (game.get(f'prop{i}'), game.get(f'min{i}'), game.get(f'max{i}')) != expected
            for i, expected in enumerate(PROPERTIES, 1)
        )
        or any(
            stat_specs.get(str(stat), {}).get(k) != 0
            for stat in BOUNDS
            for k in ('shift', 'encode', 'parameter_bits', 'op', 'op_param')
        )
        or rule.get('id') != 'crown-two-socket-shell'
        or rule.get('scope') != 'SC / Non-Ladder / PC / RotW'
        or not rule.get('evidence_ids')
        or not rule.get('guide_entries')
        or not policy.get('crown_trade_validated_at')
        or policy['crown_trade_validated_at'] != rule.get('reviewed_at')
    ):
        return None
    return {'definition': definition, 'variants': VARIANTS}


def case_gap(cases, policy, spec):
    seen, signatures = set(), set()
    inserted = set()
    incomplete = False
    for item, checks, signature in cases:
        raw = item['raw_stats']
        stats = {s: v for s, layer, v in raw if layer == 0}
        if len(stats) != len(raw) or any(type(v) is not int for v in stats.values()):
            return 'Ambiguous Crown native capture.'
        if stats.get(127) != 1 or stats.get(99) != 30:
            return 'Fixed Crown benefits missing from report inputs.'
        identified, ethereal, sockets, contents = signature
        valid_rolls = all(
            s in stats and stats[s] >= lo and (contents != 'empty' or stats[s] <= hi) for s, (lo, hi) in BOUNDS.items()
        )
        equal = contents != 'empty' or len({stats.get(s) for s in (39, 41, 43, 45)}) == 1
        candidate = (
            identified is True
            and ethereal is False
            and sockets == 2
            and item['complete'] is True
            and valid_rolls
            and equal
        )
        reason = 'Two sockets support defensive Uber setups; no proven intrinsic-roll premium.'
        if contents != 'empty':
            reason += ' Assess inserts separately.'
        lines = (
            [{'text': 'Trade: candidate — ' + reason, 'tone': 'tier_high' if contents == 'empty' else 'tier_med'}]
            if candidate
            else []
        )
        if (
            checks.get('qualification') != {'status': 'candidate' if candidate else 'unresolved'}
            or checks.get('lines') != lines
        ):
            return 'Crown trade verdict or report color is not explicitly verified.'
        signatures.add(signature)
        if signature == (True, False, 2, 'unknown') and candidate:
            inserted.update((s, stats.get(s)) for s in BOUNDS)
        incomplete |= item['complete'] is False
        if signature == (True, False, 2, 'empty') and item['complete']:
            seen.update((s, stats.get(s)) for s in BOUNDS)
    required = {(s, v) for s, (lo, hi) in BOUNDS.items() for v in (None, lo - 1, lo, hi, hi + 1)}
    if (
        not required <= seen
        or not signatures >= VARIANTS
        or not incomplete
        or not {(31, 409), (36, 26), (39, 50)} <= inserted
    ):
        return 'Missing Crown roll, socket, unknown or incomplete boundary reports.'
    return None
