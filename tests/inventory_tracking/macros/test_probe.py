import random

from inventory_tracking.macros.actuator import eased_path
from inventory_tracking.macros.probe import anything_open, data_at, writable_regions


def mapping(start, end, permissions):
    return {'start': start, 'end': end, 'permissions': permissions, 'path': ''}


def test_only_the_writable_parts_of_the_image_are_recorded():
    mappings = [
        mapping(0x1000, 0x3000, 'r-xp'),
        mapping(0x3000, 0x5000, 'rw-p'),
        mapping(0x5000, 0x9000, 'rw-p'),  # runs past the image end
        mapping(0x9000, 0xA000, 'rw-p'),  # another allocation
        mapping(0x2000, 0x2800, '-w-p'),  # not readable
    ]
    assert writable_regions(mappings, 0x1000, 0x6000) == [(0x3000, 0x2000), (0x5000, 0x2000)]


def test_bytes_are_found_by_address_across_recorded_regions():
    regions = [(0x3000, 4), (0x8000, 4)]
    data = b'abcdEFGH'
    assert data_at(data, regions, 0x8001, 2) == b'FG'
    assert data_at(data, regions, 0x3003, 2) == b''  # crosses a region end
    assert data_at(data, regions, 0x5000, 1) == b''


def test_the_pointer_path_ends_exactly_on_the_goal_and_never_jumps():
    path = eased_path((100, 100), (900, 500), 14, random.Random(1))
    assert path[-1] == (900, 500)
    steps = [abs(b[0] - a[0]) for a, b in zip([(100, 100), *path], path, strict=False)]
    assert max(steps) < 200
    assert steps[0] < steps[len(steps) // 2]  # starts slowly


def test_idle_flags_do_not_count_as_an_open_panel():
    idle = bytes.fromhex('0100000000000000000001000100000000000100010000000000000001010000')
    assert not anything_open(idle)
    menu = bytearray(idle)
    menu[0x09] = 1
    assert anything_open(bytes(menu))
