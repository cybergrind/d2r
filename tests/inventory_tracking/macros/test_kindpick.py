"""The KP_6 kind picker's rows and highlight (macros/kindpick.py; the player, 2026-10-20: "pop some kind of dialogue to
chose the mode on 3 clicks: shard act 4 as an entry")."""

import pytest

from inventory_tracking.hud.scene import Widget
from inventory_tracking.macros import kindpick
from inventory_tracking.macros.kindpick import KindPicker, entries
from inventory_tracking.macros.loop import ACT4, ANDARIEL, KINDS, LK, TZ, TZ_CLEAR, coming_kinds


OFFERED = {LK.key: LK, ANDARIEL.key: ANDARIEL, TZ.key: TZ, TZ_CLEAR.key: TZ_CLEAR}


SHARD_ACTS = [f'Shard: Act {act}' for act in range(1, 6)]


def test_the_rows_are_the_offered_kinds_in_order_then_the_shard_acts_coming():
    rows = entries(OFFERED)

    assert [row.name for row in rows] == ['Lower Kurast', 'Andariel', TZ.name, 'Full clear TZ', *SHARD_ACTS]
    assert [row.enabled for row in rows] == [True, True, True, True, False, False, False, False, False]
    assert rows[1].word == 'AND'
    assert rows[1].metric == 'Andariel kills an hour'


def test_the_default_rows_are_loop_kinds_and_the_act_kinds_not_ready_coming():
    # The player, 2026-10-20 ~22:50: "could you implement shards run for every act": one kind per act, offered once
    # its script is ready (macros/acts/), "coming" until then
    from inventory_tracking.macros import acts

    rows = entries()
    assert [row.key for row in rows][: len(KINDS)] == list(KINDS)
    coming = [row.key for row in rows if not row.enabled]
    assert coming == [f'act{act}' for act in range(1, 6) if not acts.ready(act)]
    assert 'act4' in [row.key for row in rows if row.enabled]


def test_an_act_kind_once_offered_replaces_its_coming_entry_by_itself():
    rows = entries({**OFFERED, ACT4.key: ACT4})

    assert [row.name for row in rows if row.enabled][-1] == 'Shard: Act 4'
    assert [row.name for row in rows if not row.enabled] == [name for name in SHARD_ACTS if name != 'Shard: Act 4']
    assert [coming.word for coming in coming_kinds(['act4'])] == ['ACT1', 'ACT2', 'ACT3', 'ACT5']
    assert len(coming_kinds(['andariel'])) == 5  # andariel starts with "a", not "act1"


def test_the_highlight_starts_after_the_kind_running_and_skips_the_coming_entry():
    picker = KindPicker(entries(OFFERED), TZ_CLEAR, 0.0)
    assert picker.highlighted.kind == LK  # past the coming entry, round the end

    picker = KindPicker(entries(OFFERED), ANDARIEL, 0.0)
    assert picker.highlighted.kind == TZ
    assert [picker.move(1.0).kind for _ in range(4)] == [TZ_CLEAR, LK, ANDARIEL, TZ]


def test_a_kind_not_in_the_rows_highlights_the_first():
    picker = KindPicker(entries({LK.key: LK, ANDARIEL.key: ANDARIEL}), TZ, 0.0)
    assert picker.highlighted.kind == LK


def test_no_kind_to_choose_is_refused():
    with pytest.raises(ValueError, match='kind to choose'):
        KindPicker(entries({}), LK, 0.0)


def test_it_expires_pick_seconds_after_its_last_press():
    picker = KindPicker(entries(OFFERED), LK, 10.0)
    assert not picker.expired(10.0 + kindpick.PICK_SECONDS - 0.1)
    picker.move(12.0)
    assert not picker.expired(10.0 + kindpick.PICK_SECONDS + 1)
    picker.touch(20.0)
    assert not picker.expired(20.0 + kindpick.PICK_SECONDS - 0.1)
    assert picker.expired(20.0 + kindpick.PICK_SECONDS)


def test_its_widget_marks_the_kind_running_the_one_asked_and_the_highlight():
    picker = KindPicker(entries(OFFERED), ANDARIEL, 0.0, pending=LK)

    (widget,) = picker.widgets(2.0)

    assert isinstance(widget, Widget)
    assert (widget.id, widget.kind, widget.slot) == ('picker', 'picker', 'picker')
    rows = {row['name']: row for row in widget.payload['rows']}
    assert rows['Andariel']['current']
    assert rows['Lower Kurast']['pending']
    assert rows[TZ.name]['highlighted']
    coming = rows['Shard: Act 4']
    assert not coming['enabled']
    assert not coming['highlighted']
    assert (coming['note'], coming['word']) == ('coming', 'ACT4')
    assert widget.payload['title'] == 'Loop kind'
    assert widget.payload['hint'].endswith('4 s')  # the seconds left
