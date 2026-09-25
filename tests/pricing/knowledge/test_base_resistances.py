from pricing.knowledge.base_resistances import resistance_options


def test_base_resistance_options_preserve_discrete_rolls_and_nonresistance_alternative():
    rows = {
        'res': {'group': 1, 'spawnable': 1, 'mod1code': 'res-all', 'mod1min': 5, 'mod1max': 6},
        'damage': {'group': 1, 'spawnable': 1, 'mod1code': 'dmg%', 'mod1min': 10, 'mod1max': 20},
    }
    assert resistance_options({'auto prefix': 1}, rows) == [0, 5, 6]
    assert resistance_options({'auto prefix': 2}, rows) is None
    assert resistance_options({}, rows) == [0]
    assert resistance_options({'auto prefix': 1}, {**rows, 'res': {**rows['res'], 'mod1code': 'res-fire'}}) is None


def test_catalog_compiles_base_resistance_choices_with_source_provenance(tmp_path):
    import json

    from pricing.knowledge.legacy import import_catalog

    raw = tmp_path / 'pricing/raw'
    raw.mkdir(parents=True)
    (raw / 'd2data-armor.json').write_text(
        json.dumps(
            {
                'shield': {'name': 'Fixture shield', 'code': 'fixture', 'auto prefix': 1},
            }
        )
    )
    table = tmp_path / 'third-parties/d2data/json/automagic.json'
    table.parent.mkdir(parents=True)
    table.write_text(json.dumps({'r': {'group': 1, 'spawnable': 1, 'mod1code': 'res-all', 'mod1min': 5, 'mod1max': 6}}))
    document = import_catalog(tmp_path)
    assert document['rows'][0]['details']['base_resistance_options'] == [5, 6]
    assert any(s['path'] == str(table.relative_to(tmp_path)) and s['sha256'] for s in document['sources'])
    table.unlink()
    assert import_catalog(tmp_path)['rows'][0]['details']['base_resistance_options'] is None
