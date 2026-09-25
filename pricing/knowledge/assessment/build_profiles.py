"""Compile and atomically publish reviewed build profiles from offline sources."""

import json
import os
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / 'pricing/data/appraisal-build-profiles.json'


RULES = Path(__file__).resolve().parent / 'rules/reviewed_profiles.json'


def build(root=ROOT):
    from pricing.knowledge.assessment.maintenance.compile import compile_profiles
    from pricing.knowledge.assessment.maintenance.rule_bundle import load_rule_bundle

    result = compile_profiles(load_rule_bundle(RULES), root)
    review_path = Path(root) / 'pricing/knowledge/assessment/rules/guide_use_reviews.json'
    if review_path.exists():
        from pricing.knowledge.assessment.maintenance.guide_demand import compile_demand

        reviews = json.loads(review_path.read_text())
        if reviews.get('schema_version') != 1:
            raise ValueError('Unsupported guide-use review schema')
        result['guide_demand'] = {
            'uses': reviews['uses'],
            'summaries': compile_demand(reviews['uses'], result['profiles']),
        }
    stat_path = Path(root) / 'pricing/knowledge/assessment/rules/stat_use_reviews.json'
    if stat_path.exists():
        from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
        from pricing.knowledge.assessment.stat_bundle import configuration_row

        reviews = json.loads(stat_path.read_text())
        if reviews.get('schema_version') != 1:
            raise ValueError('Unsupported stat review schema')
        result['stat_evaluation'] = {
            'reviews': reviews['reviews'],
            'configurations': [
                configuration_row(c)
                for c in compile_stat_configurations(reviews['reviews'], result['profiles'], root=root)
            ],
        }
    return result


def main():
    from pricing.knowledge.assessment.profiles import validate_profiles

    result = build()
    validate_profiles(result['profiles'])
    payload = json.dumps(result, indent=2, allow_nan=False) + '\n'
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8', dir=OUTPUT.parent, prefix=OUTPUT.name + '.', suffix='.tmp', delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, OUTPUT)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(json.dumps(result['coverage']))


if __name__ == '__main__':
    main()
