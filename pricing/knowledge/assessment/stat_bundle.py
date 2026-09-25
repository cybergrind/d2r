"""Prepared stat configurations and semantic validation; no source-file reads."""

from dataclasses import fields

from pricing.knowledge.assessment.domain.facts import thaw
from pricing.knowledge.assessment.stat_evaluation import StatConfiguration, StatPriority


def configuration_row(config):
    row = {field.name: thaw(getattr(config, field.name)) for field in fields(config) if field.name != 'priorities'}
    row['priorities'] = [{field.name: thaw(getattr(p, field.name)) for field in fields(p)} for p in config.priorities]
    if not config.advisory_conditions:
        row.pop('advisory_conditions')
    return row


def configuration_from_row(row):
    return StatConfiguration(**{**row, 'priorities': tuple(StatPriority(**p) for p in row['priorities'])})


def validate_stat_bundle(document):
    if 'stat_evaluation' not in document:
        return
    from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations

    bundle = document['stat_evaluation']
    expected = [configuration_row(c) for c in compile_stat_configurations(bundle['reviews'], document['profiles'])]
    if expected != bundle['configurations']:
        raise ValueError('Published stat configuration differs from reviewed source-linked role')
