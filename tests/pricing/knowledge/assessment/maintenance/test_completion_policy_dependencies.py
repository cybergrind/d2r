"""A final attestation must not survive changed mercenary-context review semantics."""

import shutil
from pathlib import Path

import pytest

from pricing.knowledge.assessment.maintenance import completion


@pytest.mark.parametrize(
    'helper',
    [
        'planner_fcr.py',
        'spirit_loadout_endorsement.py',
        'spirit_planner_links.py',
        'sazabi_loadout_endorsement.py',
        'sazabi_planner_links.py',
        'named_socket_endorsement.py',
        'named_planner_links.py',
        '../../definitions.py',
        'context_values.py',
        'value_scope_manifest.py',
        'seasonal_named_audit.py',
        'mercenary_source_context.py',
        'player_utility_context.py',
        'socket_component_context.py',
        'named_prose_context.py',
        'reward_mentions.py',
        'hardcore_mentions.py',
        'embedded_abyss_recipes.py',
        'embedded_echoing_fade.py',
        'embedded_echoing_malice.py',
        'embedded_echoing_insight.py',
        'merc_survival_templates.py',
        'embedded_echoing_starter.py',
        'embedded_echoing_cure.py',
        'embedded_echoing_enigma.py',
        'embedded_echoing_enchant.py',
        'embedded_echoing_pairing.py',
        'embedded_occurrences.py',
        'embedded_negative.py',
        '../../negative_mentions.py',
        'utility_source_reviews.py',
        'guide_positions.py',
        '../policies/consumables.py',
    ],
)
def test_completion_scope_tracks_mercenary_review_helpers(tmp_path, monkeypatch, helper):
    relative = 'pricing/knowledge/assessment/maintenance'
    shutil.copytree(completion.ROOT / relative, tmp_path / relative, ignore=shutil.ignore_patterns('__pycache__'))
    for name in ('builds.py', 'negative_mentions.py', 'definitions.py'):
        relative_source = Path('pricing/knowledge') / name
        shutil.copyfile(completion.ROOT / relative_source, tmp_path / relative_source)
    policy = Path('pricing/knowledge/assessment/policies/consumables.py')
    (tmp_path / policy).parent.mkdir(parents=True)
    shutil.copyfile(completion.ROOT / policy, tmp_path / policy)
    monkeypatch.setattr(completion, 'ROOT', tmp_path)
    before = completion.policy_fingerprint()
    source = tmp_path / relative / helper
    source.write_text(source.read_text() + '\n# Simulated reviewed-semantics change.\n')
    assert completion.policy_fingerprint() != before
