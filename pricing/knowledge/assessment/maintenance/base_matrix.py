"""Maintenance-only base coverage dimensions; links never establish item fit or price."""

import hashlib
import json
from collections import Counter

from pricing.knowledge.assessment.maintenance.base_policy_membership import BasePolicyMembership, catalog_facts
from pricing.knowledge.assessment.maintenance.inventory import ROOT
from pricing.knowledge.assessment.maintenance.recipe_eligibility import audit_recipe_membership


QUALITIES = ('normal', 'superior', 'low_quality')


def state(value, reason):
    return {'state': value, 'reason': reason}


def audit_bases(bases, types, utility_rows, profiles, market, *, recipes=None, base_use_evaluator=None):
    market_by_code = {r['code']: r for r in market.get('bases', [])}
    membership_index = BasePolicyMembership(profiles)
    rows = []
    for code, base in sorted(bases.items()):
        cap = base.get('gemsockets', 0)
        record = types.get(base.get('type'), {})
        limits = [record.get(key) for key in ('MaxSockets1', 'MaxSockets2', 'MaxSockets3')]
        known = type(cap) is int and 0 <= cap <= 6 and (cap == 0 or all(type(n) is int and 0 <= n <= 6 for n in limits))
        expected = ([min(cap, n) for n in limits] if cap else [0, 0, 0]) if known else None
        edges = [
            r
            for r in utility_rows
            if r.get('base_code') == code and r.get('details', {}).get('legality') == 'verified_type_and_capacity'
        ]
        conflicts = sorted(
            {
                r.get('source_locator', '')
                for r in edges
                if r['details'].get('socket_options', {}).get('maximum_by_ilvl_bracket') != expected
            }
        )
        links = sorted({(r['details']['runeword'], r.get('source_locator', '')) for r in edges})
        membership = audit_recipe_membership(base, types, recipes, edges)
        for quality in QUALITIES:
            assignments = membership_index.assignments(code, base, quality)
            candidates = [row['profile_id'] for row in assignments if row['guard_truth'] != 'false']
            base_uses = base_use_evaluator(catalog_facts(code, base, quality)) if base_use_evaluator else []
            rows.append(
                {
                    'id': f'{code}:{quality}',
                    'base_code': code,
                    'name': base['name'],
                    'quality': quality,
                    'base_type': base.get('type'),
                    'native_locator': f'{base.get("_table", "bases")}/{code}',
                    'socket_caps': expected,
                    'socket_conflicts': conflicts,
                    'recipe_links': [{'runeword': name, 'source_locator': locator} for name, locator in links],
                    'candidate_profile_ids': candidates,
                    'policy_assignments': assignments,
                    'base_uses': base_uses,
                    'base_market_evidence': market_by_code.get(code),
                    'recipe_membership': membership,
                    'dimensions': {
                        'discovery': state(
                            'reviewed', 'Native catalog identity retained, including unmentioned bases.'
                        ),
                        'socket_mechanics': state(
                            'reviewed' if known and not conflicts else 'blocked',
                            'Native caps agree with cached edges; recipe/mode eligibility remains separate.'
                            if known and not conflicts
                            else 'Missing native limits or conflicting cached socket caps.',
                        ),
                        'type_capacity_eligibility': state(membership['state'], membership['reason']),
                        'recipe_eligibility': state(
                            'pending', 'Type/capacity links do not verify every recipe, mode or quality route.'
                        ),
                        'base_use_routing': state(
                            'reviewed' if base_use_evaluator else 'pending',
                            'Runtime base-use routing audited with partial facts; not item fit.'
                            if base_use_evaluator
                            else 'Runtime base-use audit was not supplied.',
                        ),
                        'policy_routing': state(
                            'reviewed', 'Runtime selectors and partial-fact guards evaluated; not item fit.'
                        ),
                        'desirability': state(
                            'pending',
                            'Unexcluded rule assignments still require item-specific facts and reviewed use coverage.',
                        ),
                        'stat_annotations': state(
                            'pending', 'Per-configuration stat combinations and roll annotations need review.'
                        ),
                        'named_tiers': state(
                            'excluded', 'Base-quality rows are not unique/set identities; named audit is separate.'
                        ),
                        'report': state(
                            'pending', 'Saved examples do not establish report coverage for every base/quality.'
                        ),
                        'market': state(
                            'pending',
                            'Base-level observations do not establish quality/ethereal/socket/roll-matched cohorts.',
                        ),
                    },
                }
            )
    counts = (
        {
            dimension: dict(sorted(Counter(r['dimensions'][dimension]['state'] for r in rows).items()))
            for dimension in rows[0]['dimensions']
        }
        if rows
        else {}
    )
    return {
        'schema_version': 1,
        'complete': False,
        'scope': 'Base qualities only; not the full all-item matrix',
        'counts': {
            'base_identities': len(bases),
            'base_quality_rows': len(rows),
            'dimensions': counts,
            'base_use_rows': sum(bool(r['base_uses']) for r in rows),
            'base_uses': sum(len(r['base_uses']) for r in rows),
        },
        'rows': rows,
    }


def main():
    from pricing.knowledge.assessment.base_use import assess_runeword_base

    paths = {
        'weapons': ROOT / 'third-parties/d2data/json/weapons.json',
        'armor': ROOT / 'third-parties/d2data/json/armor.json',
        'types': ROOT / 'third-parties/d2data/json/itemtypes.json',
        'recipes': ROOT / 'third-parties/d2data/json/runes.json',
        'utility': ROOT / 'pricing/data/appraisal-utility.json',
        'profiles': ROOT / 'pricing/data/appraisal-build-profiles.json',
        'market': ROOT / 'pricing/data/appraisal-base-coverage.json',
    }
    raw = {key: path.read_bytes() for key, path in paths.items()}
    data = {key: json.loads(value) for key, value in raw.items()}
    bases = {code: {**base, '_table': table} for table in ('weapons', 'armor') for code, base in data[table].items()}
    result = audit_bases(
        bases,
        data['types'],
        data['utility']['rows'],
        data['profiles']['profiles'],
        data['market'],
        recipes=data['recipes'],
        base_use_evaluator=assess_runeword_base,
    )
    result['sources'] = {
        key: {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(raw[key]).hexdigest()}
        for key, path in paths.items()
    }
    for name in (
        'base_use.py',
        'caster_base_templates.py',
        'progression_base_templates.py',
        'mechanics/preparation.py',
        'mechanics/low_quality.py',
    ):
        path = ROOT / 'pricing/knowledge/assessment' / name
        result['sources']['implementation:' + name] = {
            'path': str(path.relative_to(ROOT)),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    metadata = ROOT / 'inventory_tracking/items/data/item_metadata.json'
    result['sources']['runtime_metadata'] = {
        'path': str(metadata.relative_to(ROOT)),
        'sha256': hashlib.sha256(metadata.read_bytes()).hexdigest(),
    }
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
