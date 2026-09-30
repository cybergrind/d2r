"""Hash-pinned planner reachability audit; source exclusions require later review."""

import hashlib
import json
from collections import defaultdict
from pathlib import Path

from pricing.knowledge.assessment.maintenance.planner_reachability import guide_references, planner_reachability
from pricing.knowledge.builds import load_catalog
from pricing.knowledge.refresh import atomic_json


ROOT = Path(__file__).resolve().parents[4]


def audit_sources(inventory, root, *, catalog_ids):
    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint

    root = Path(root).resolve()
    refs = defaultdict(set)
    reference_sources = defaultdict(list)
    guide_issues, source_issues, unsupported = [], [], []
    reports, hashes, documents = {}, {}, {}
    for source in inventory['sources']:
        name = source['path']
        path = (root / name).resolve()
        is_planner = '/planners/' in name and path.name not in ('game-data.json', 'game-strings.json')
        if path.suffix != '.html' and not is_planner:
            continue
        if not path.is_relative_to(root):
            source_issues.append({'source': name, 'reason': 'outside repository'})
            continue
        try:
            raw = path.read_bytes()
        except OSError as exc:
            source_issues.append({'source': name, 'reason': str(exc)})
            continue
        hashes[name] = hashlib.sha256(raw).hexdigest()
        if hashes[name] != source.get('sha256'):
            source_issues.append({'source': name, 'reason': 'missing or mismatched source hash'})
            continue
        try:
            if is_planner:
                documents[name] = json.loads(raw)
            else:
                result = guide_references(raw.decode(), catalog_ids=catalog_ids)
                for key, value in result['references'].items():
                    refs[key].update(value)
                    reference_sources[key].append({'source': name, 'item_ids': value})
                guide_issues.extend({'source': name, **issue} for issue in result['issues'])
        except (ValueError, UnicodeError) as exc:
            source_issues.append({'source': name, 'reason': str(exc)})
    for name, document in sorted(documents.items()):
        try:
            reports[name] = planner_reachability(document, refs[Path(name).stem])
        except (ValueError, AttributeError, TypeError) as exc:
            unsupported.append({'source': name, 'error': str(exc)})
    missing = sorted(set(refs) - {Path(path).stem for path in reports})
    if source_issues or guide_issues or unsupported or missing:
        for report in reports.values():
            # Incomplete global references cannot prove local absence.
            report['unreachable_candidates'] = []
    return {
        'schema_version': 1,
        'inventory_fingerprint': fingerprint(inventory),
        'exclusions_approved': False,
        'scope': 'Source diagnostics only; no identity, configuration or pricing disposition.',
        'source_hashes': hashes,
        'planner_reports': reports,
        'guide_issues': guide_issues,
        'source_issues': source_issues,
        'unsupported_sources': unsupported,
        'missing_planners': missing,
        'guide_reference_sources': dict(sorted(reference_sources.items())),
    }


def main():
    from pricing.knowledge.assessment.maintenance.planner_context_reviews import apply_context_reviews

    inventory = ROOT / 'pricing/data/appraisal-guide-inventory.json'
    raw = inventory.read_bytes()
    game_path = ROOT / 'pricing/raw/mr/planners/game-data.json'
    game_raw = game_path.read_bytes()
    game = json.loads(game_raw)
    # Crafted tooltip identifiers belong to the planner's recipe catalog too.
    catalog_ids = set(load_catalog(ROOT)) | set(game['crafted'])
    result = audit_sources(json.loads(raw), ROOT, catalog_ids=catalog_ids)
    review_path = 'pricing/knowledge/assessment/rules/planner_context_reviews.json'
    review_raw = (ROOT / review_path).read_bytes()
    reviews = json.loads(review_raw)
    documents = {row['source']: json.loads((ROOT / row['source']).read_bytes()) for row in reviews['rows']}
    apply_context_reviews(result, documents, reviews, ROOT)
    result['source_hashes'][review_path] = hashlib.sha256(review_raw).hexdigest()
    for row in reviews['rows']:
        result['source_hashes'].update({ref['path']: ref['sha256'] for ref in row['evidence']})
    result['inventory_sha256'] = hashlib.sha256(raw).hexdigest()
    result['catalog_sha256'] = hashlib.sha256(game_raw).hexdigest()
    atomic_json(ROOT / 'pricing/data/appraisal-planner-reachability.json', result)
    print(
        json.dumps(
            {
                'planners': len(result['planner_reports']),
                'guide_issues': len(result['guide_issues']),
                'source_issues': len(result['source_issues']),
                'unsupported_sources': result['unsupported_sources'],
                'exclusions_approved': False,
            }
        )
    )


if __name__ == '__main__':
    main()
