from html import unescape
from xml.etree import ElementTree

from inventory_tracking.appraisal.presentation import ItemAssessment
from inventory_tracking.presentation import Tone, render_markup
from tests.inventory_tracking.appraisal.test_text import saved_result


def test_shared_assessment_preserves_text_and_semantics_in_both_renderers():
    record = saved_result()
    extraction = record['result']['extraction']
    extraction['item']['rarity'] = 'unique'
    extraction['decoded_stats'] = [
        {'status': 'decoded', 'text': '+40 Resist', 'roll_quality': 'perfect'},
        {'status': 'decoded', 'text': '+1 Strength', 'roll_quality': 'low'},
        {'status': 'unresolved', 'text': 'Unknown <stat> & value'},
    ]
    assessment = ItemAssessment.from_record(record)
    osd = assessment.to_osd()
    assert osd[0].tone == Tone.UNIQUE
    assert next(line for line in osd if '+40 Resist' in line.text).tone == Tone.PERFECT
    assert next(line for line in osd if '+1 Strength' in line.text).tone == Tone.LOW
    assert next(line for line in osd if 'Unknown <stat>' in line.text).tone == Tone.WARNING
    assert assessment.to_rich().plain == assessment.to_text()
    markup = render_markup(osd)
    root = ElementTree.fromstring('<root>' + markup + '</root>')
    assert ''.join(root.itertext()) == '\n'.join(line.text for line in osd)
    assert 'Container:' in assessment.to_text()
    assert 'Container:' not in unescape(markup)


def test_markup_and_rich_control_sequences_remain_literal():
    record = saved_result()
    record['result']['extraction']['item']['name'] = '<b>Ring & [red]Amulet</b>'
    assessment = ItemAssessment.from_record(record)
    assert '<b>Ring & [red]Amulet</b>' in assessment.to_rich().plain
    markup = render_markup(assessment.to_osd())
    assert '&lt;b&gt;Ring &amp; [red]Amulet&lt;/b&gt;' in markup
    assert '<b>Ring' not in markup


def test_shared_document_keeps_rejection_reason_and_no_price():
    assessment = ItemAssessment.from_record({'request_id': 2, 'state': 'rejected', 'reason': 'Hover lost'})
    assert 'Unavailable: Hover lost' in assessment.to_text()
    assert assessment.to_osd()[0].tone == Tone.WARNING
    assert 'Price:' not in assessment.to_text()


def test_roll_styles_are_attached_to_rows_not_matching_text():
    record = saved_result()
    record['result']['extraction']['decoded_stats'] = [
        {'status': 'decoded', 'text': 'Same label', 'roll_quality': 'perfect'},
        {'status': 'decoded', 'text': 'Same label', 'roll_quality': 'low'},
    ]
    rows = [line for line in ItemAssessment.from_record(record).to_osd() if 'Same label' in line.text]
    assert [line.tone for line in rows] == [Tone.PERFECT, Tone.LOW]


def test_published_osd_retains_semantic_colors(tmp_path):
    import time

    from inventory_tracking.hud.payloads import card_lines
    from inventory_tracking.hud.process import card_widgets
    from inventory_tracking.hud.scene import publish_layer, read_scene

    lines = ItemAssessment.from_record(saved_result()).to_osd()
    publish_layer(tmp_path, 'appraisal', card_widgets(lines))
    [widget] = read_scene(tmp_path, now=time.monotonic())
    assert card_lines(widget.payload) == lines
    publish_layer(tmp_path, 'appraisal', [])
    assert read_scene(tmp_path, now=time.monotonic()) == []


def test_trade_and_leveling_tiers_share_readable_colors():
    from rich.style import Style

    from inventory_tracking.presentation import PALETTE

    colors = {'high': '#55ff55', 'med': '#ffff55', 'low': '#77aaff', 'trash': '#ff5555'}
    for tier, color in colors.items():
        record = saved_result()
        record['result']['assessment'] = {
            'trade_tier': {'status': 'reviewed', 'tier': tier, 'source': {'date': '2026-09-26'}},
            'leveling': [
                {
                    'tier': tier,
                    'classes': ['Sorceress'],
                    'side': 'player',
                    'archetypes': ['caster'],
                    'reason': 'Leveling use',
                    'conditions': [],
                }
            ],
        }
        document = ItemAssessment.from_record(record)
        rows = [line for line in document.to_osd() if line.text.startswith(('Trade tier:', 'Leveling:'))]
        assert len(rows) == (2 if tier == 'high' else 1)
        for row in rows:
            assert Style.parse(PALETTE[row.tone]).color.get_truecolor().hex == color
            assert color in render_markup([row])
        assert document.to_rich().plain == document.to_text()


def test_owned_copies_show_after_the_stats_with_the_best_copy_on_the_osd():
    record = saved_result()
    record['result']['owned'] = {
        'kind': 'unique Snowclash',
        'count': 3,
        'relation': 'worse',
        'perfection': 0.5,
        'copies': [
            {
                'location': f'Mule · stash ({x},0)',
                'identical': False,
                'perfection': p,
                'relation': r,
                'better': [],
                'worse': w,
            }
            for x, p, r, w in [(0, 0.2, 'better', []), (1, 0.9, 'worse', ['CR +12% vs 15']), (2, 0.4, 'mixed', [])]
        ],
    }
    document = ItemAssessment.from_record(record)
    texts = [line.text for line in document.lines]
    header = texts.index('Owned: 3 x unique Snowclash — an owned copy rolls better; rolls 50% of max')
    assert texts[header + 1] == '  Mule · stash (1,0) (90% rolls) — worse — new worse: CR +12% vs 15'
    assert document.lines[header].tone == Tone.LOW
    osd = [line.text for line in document.to_osd()]
    assert texts[header + 1] in osd
    assert texts[header + 2] not in osd


def test_owned_jewel_comparison_is_neutral_and_not_a_keep_limit():
    record = saved_result()
    record['result']['extraction']['item'].update(name='Jewel', base_name='Jewel', rarity='magic')
    record['result']['owned'] = {
        'kind': 'magic Jewel with the same stats',
        'count': 2,
        'relation': 'worse',
        'perfection': 0.89,
        'copies': [],
    }
    document = ItemAssessment.from_record(record)
    header = next(line for line in document.lines if line.text.startswith('Owned:'))
    assert header.tone == Tone.METADATA
    assert header.text == 'Owned: 2 x magic Jewel with the same stats'
