"""Prepare native FCR and companion evidence for selected Hammerdin Spirit uses."""

import hashlib
import json

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.inventory import ROOT
from pricing.knowledge.assessment.maintenance.planner_fcr import SOURCE_PATHS, active_fcr_evidence
from pricing.knowledge.builds import decode_planner
from pricing.knowledge.refresh import atomic_json


PROFILE_IDS = ('hammer-standard-spirit-shield', 'hammer-mf-spirit-shield')


def build(root=ROOT):
    inputs, cache = {}, {}

    def read(path):
        if path not in cache:
            raw = (root / path).read_bytes()
            inputs[path] = hashlib.sha256(raw).hexdigest()
            cache[path] = json.loads(raw)
        return cache[path]

    profiles = {r['id']: r for r in read('pricing/data/appraisal-build-profiles.json')['profiles']}
    reviewed_occurrences = set()
    registry = 'pricing/knowledge/assessment/rules/spirit_planner_reviews.json'
    if (root / registry).exists():
        from pricing.knowledge.assessment.maintenance.spirit_planner_links import compile_spirit_planner_links

        reviewed_occurrences = {
            row['occurrence_id']
            for row in compile_spirit_planner_links(
                read(registry),
                read('pricing/data/appraisal-guide-inventory.json'),
                list(profiles.values()),
                read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'],
                root,
            )
        }
    candidates = read('pricing/data/appraisal-planner-candidate-tab-audit.json')['rows']
    tables = {key: read(path) for key, path in SOURCE_PATHS.items()}
    rows = []
    for profile_id in PROFILE_IDS:
        role = profiles[profile_id]
        matches = [r for r in candidates if r['profile_id'] == profile_id and r['state'] == 'exact_tab_reference']
        if len(matches) != 1:
            raise ValueError('Spirit loadout audit requires one selected planner example')
        candidate = matches[0]
        planner = decode_planner(read(candidate['planner_path']))
        profile = planner['profiles'][candidate['planner_profile_index']]
        result = active_fcr_evidence(profile, planner['items'], tables)
        names = {r['name'] for r in result['contributors']}
        dependencies = []
        for dependency in role.get('depends_on', []):
            predicate = dependency['when']
            if predicate['op'] == 'context_at_least' and predicate['field'] == 'player_total_fcr':
                matched = result['minimum_fcr'] >= predicate['value']
            elif predicate['op'] == 'context_contains' and predicate['field'] == 'player_items':
                matched = predicate['value'] in names
            else:
                raise ValueError('Spirit loadout audit encountered an unsupported dependency')
            dependencies.append({'requirement': dependency, 'matched': matched})
        item_id = str(profile['items']['larm'])
        rows.append(
            {
                'profile_id': profile_id,
                'profile_sha256': fingerprint(role),
                'parent_occurrence_id': candidate['parent_occurrence_id'],
                'planner': {'path': candidate['planner_path'], 'sha256': inputs[candidate['planner_path']]},
                'profile_index': candidate['planner_profile_index'],
                'profile_uid': profile['uid'],
                'item_id': item_id,
                'item': planner['items'][item_id],
                'fcr_evidence': result,
                'dependencies': dependencies,
                'state': (
                    'reviewed_source_occurrence'
                    if candidate['parent_occurrence_id'] in reviewed_occurrences
                    else 'pending_full_source_endorsement'
                ),
            }
        )
    for name in (
        'planner_fcr.py',
        'spirit_loadout_audit.py',
        'spirit_loadout_endorsement.py',
        'spirit_planner_links.py',
    ):
        path = 'pricing/knowledge/assessment/maintenance/' + name
        inputs[path] = hashlib.sha256((root / path).read_bytes()).hexdigest()
    return {
        'schema_version': 1,
        'complete': False,
        'review_date': '2026-09-30',
        'scope': 'Native FCR, companions and validated source links; no pricing or full assessment claim.',
        'inputs': inputs,
        'rows': rows,
    }


def main():
    result = build()
    atomic_json(ROOT / 'pricing/data/appraisal-spirit-loadout-audit.json', result)
    print(
        json.dumps(
            [
                {
                    'profile_id': row['profile_id'],
                    'minimum_fcr': row['fcr_evidence']['minimum_fcr'],
                    'requirements_matched': all(d['matched'] for d in row['dependencies']),
                    'state': row['state'],
                }
                for row in result['rows']
            ]
        )
    )


if __name__ == '__main__':
    main()
