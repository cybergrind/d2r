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

    from inventory_tracking.appraisal.overlay import publish_display, read_display

    path = tmp_path / 'osd.json'
    record = saved_result()
    publish_display(path, record)
    assert read_display(path, time.monotonic()) == ItemAssessment.from_record(record).to_osd()
    publish_display(path, None)
    assert read_display(path, time.monotonic()) == []
