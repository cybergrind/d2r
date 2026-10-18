"""A played one-game TZ log is the receipt for promoting its arm to several games."""

from inventory_tracking.routes.tz_pilot import validated_receipt, write_receipt


def pilot_lines(itinerary, *, omit=(), include_tower=True):
    lines = ['2026-10-18 22:30:01 INFO Macro: Creating cyberrd80']
    if itinerary[0] == 6:
        areas = [6, 11, 15, 20, 21, 22, 23, 24, 25] if include_tower else [6, 11, 15, 21, 22, 23, 24, 25]
        lines.append(f'2026-10-18 22:30:10 INFO TZ town memory: areas {areas}; effect Cold Enchanted')
    for area in itinerary:
        if area == 20 and not include_tower:
            continue
        lines.append(f'2026-10-18 22:31:00 INFO TZ area {area}: travel observed')
        if area == 9 or area == 25:
            lines.append(f'2026-10-18 22:31:01 INFO TZ area {area}: boss killed observed')
        if area == 13 or area == 15:
            lines.append(f'2026-10-18 22:31:01 INFO TZ area {area}: chest opened observed')
        if area not in omit:
            lines.append(f'2026-10-18 22:31:02 INFO TZ area {area}: loot clear observed')
    lines.append('2026-10-18 22:32:00 INFO TZ slice: maximum games reached; report {}')
    return lines


def test_successful_cave_pilot_promotes_only_with_its_persisted_log_receipt(tmp_path):
    itinerary = (3, 9, 13)
    log = tmp_path / 'probe.log'
    log.write_text('\n'.join(pilot_lines(itinerary)) + '\n', encoding='utf-8')
    receipt = tmp_path / 'tz-pilot-receipt.json'

    write_receipt(log, receipt, itinerary)

    assert validated_receipt(receipt, itinerary)
    assert not validated_receipt(receipt, (6, 11, 15, 20, 21, 22, 23, 24, 25))
    log.write_text(log.read_text(encoding='utf-8') + '2026-10-18 22:34:00 INFO unrelated service line\n')
    assert validated_receipt(receipt, itinerary)  # later service lines do not change the proven prefix


def test_tower_pilot_requires_both_targets_and_every_terrorized_area(tmp_path):
    itinerary = (6, 11, 15, 20, 21, 22, 23, 24, 25)
    log = tmp_path / 'probe.log'
    receipt = tmp_path / 'tz-pilot-receipt.json'
    log.write_text('\n'.join(pilot_lines(itinerary, omit=(15,))) + '\n', encoding='utf-8')
    assert not validated_receipt(receipt, itinerary)
    try:
        write_receipt(log, receipt, itinerary)
    except ValueError:
        pass
    else:
        raise AssertionError('a pilot without Hole 2 loot must not make a receipt')

    log.write_text('\n'.join(pilot_lines(itinerary, include_tower=False)) + '\n', encoding='utf-8')
    write_receipt(log, receipt, itinerary)
    assert validated_receipt(receipt, itinerary)  # area 20 was transit, not in the town memory TZ list

    log.write_text(log.read_text(encoding='utf-8').replace('chest opened observed', 'chest failed observed'))
    assert not validated_receipt(receipt, itinerary)
