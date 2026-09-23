import struct

import pytest

from inventory_tracking.native import socket_items


def setup_reader(monkeypatch):
    monkeypatch.setattr(socket_items, 'unit_matches', lambda *args: True)
    monkeypatch.setattr(socket_items, 'describe_item', lambda read, unit: unit['details'])
    parent = {'address': 0x9000}
    child = {'mode': 6, 'data_pointer': 0x10000, 'details': {'x': 0}, 'unit_id': 8, 'txt_id': 1}
    memory = {0x100A0: struct.pack('<Q', 0x20000), 0x20008: struct.pack('<Q', 0x9000), 0x10000: bytes(0x60)}
    return parent, child, memory


def test_only_children_linked_to_selected_parent_are_reported(monkeypatch):
    parent, child, memory = setup_reader(monkeypatch)
    result = socket_items.read_socket_items(lambda a, n: memory[a], parent, [child])
    assert result['children'][0]['unit']['unit_id'] == 8
    memory[0x20008] = struct.pack('<Q', 0x9001)
    assert socket_items.read_socket_items(lambda a, n: memory[a], parent, [child])['children'] == []


def test_parent_link_mutation_rejects_socket_contents(monkeypatch):
    parent, child, memory = setup_reader(monkeypatch)
    reads = 0

    def read(address, size):
        nonlocal reads
        if address == 0x20008:
            reads += 1
            if reads == 2:
                return struct.pack('<Q', 0x9001)
        return memory[address]

    with pytest.raises(ValueError, match='linkage changed'):
        socket_items.read_socket_items(read, parent, [child])
