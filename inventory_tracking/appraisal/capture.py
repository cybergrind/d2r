"""Host-only request capture; freeze one selected item before local KB work."""

import copy
import os
import time
from typing import Any

from inventory_tracking.common import timestamp
from inventory_tracking.hover.sampling import capture_ui_sample, observe_ui
from inventory_tracking.hover.selection import resolve_selection
from inventory_tracking.input.focus import NiriFocusProbe, owns_process
from inventory_tracking.input.keyboard import X11Keyboard
from inventory_tracking.items.context import viewer_context
from inventory_tracking.items.decode import decode_items
from inventory_tracking.items.modifiers import owned_damage_modifiers, owned_defense_modifiers
from inventory_tracking.models import SessionIdentity
from inventory_tracking.native.image_probe import read_mappings
from inventory_tracking.native.item_diagnostics import capture_stat_candidates
from inventory_tracking.native.layout import SUPPORTED_SHA256
from inventory_tracking.native.process import identity, process_mappings
from inventory_tracking.native.resource_probe import read_item_arrays
from inventory_tracking.native.socket_items import read_socket_items
from inventory_tracking.native.unit_probe import ResearchReader, sample_units
from inventory_tracking.native.units import describe_item, unit_matches


def selected_observation(snapshot, report, unit_id, *, inventory_page=0, selection_sample=None, image_base=None):
    frozen = copy.deepcopy(snapshot)
    frozen['resources']['items'] = [r for r in frozen['resources']['items'] if r['unit_id'] == unit_id]
    if len(frozen['resources']['items']) != 1:
        raise ValueError('Selected item missing or ambiguous in stat snapshot')
    owner_id = None
    owner_type = 0
    if selection_sample is not None:
        if selection_sample['snapshot'] != snapshot:
            raise ValueError('Selection snapshot mismatch')
        selection = resolve_selection(selection_sample, image_base)
        if (
            selection['status'] != 'candidate'
            or selection['item']['unit_id'] != unit_id
            or selection['container']['page'] != inventory_page
            or any(
                selection['item'][key] != frozen['resources']['items'][0][key] for key in ('txt_id', 'mode', 'details')
            )
        ):
            raise ValueError('Selected item provenance mismatch')
        owner_id = selection['owner_id']
        owner_type = selection['owner_type']
    observations = decode_items(
        frozen, report, inventory_page=inventory_page, inventory_owner_id=owner_id, inventory_owner_type=owner_type
    )
    if len(observations) != 1 or observations[0]['source']['unit_id'] != unit_id:
        raise ValueError('Selected item does not belong to the verified inventory owner')
    return observations[0]


def game_focused(images):
    token = images['identity']
    session = SessionIdentity(token['pid'], token['start_ticks'], 0)
    if not NiriFocusProbe()(session):
        return False
    with X11Keyboard().connect() as connection:
        return connection is not None and owns_process(connection.focused_window_pid(), session)


def verify_item(pid, images, item, expected_arrays=None, *, socket_candidates=None) -> dict[str, Any]:
    """Recheck selected header, location and all recorded stats through fresh reads."""
    if identity(pid) != images['identity']:
        raise ValueError('Game process changed')
    before = process_mappings(pid)
    fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
    try:
        reader = ResearchReader(fd, before)
        item_data = reader.read(item['data_pointer'], 0x60)
        if not unit_matches(reader.read, item) or describe_item(reader.read, item) != item['details']:
            raise ValueError('Selected item changed')
        arrays: dict[str, Any] = (
            read_item_arrays(reader.read, item['stats_pointer'])
            if item['stats_pointer']
            else {
                'complete': True,
                'arrays': [{'header_offset': offset, 'stats': []} for offset in (0x30, 0xA8, 0xE8)],
            }
        )
        diagnostics = capture_stat_candidates(reader.read, item['stats_pointer']) if item['stats_pointer'] else {}
        damage = owned_damage_modifiers(diagnostics, item)
        if damage:
            arrays['damage_modifiers'] = damage
        defense = owned_defense_modifiers(diagnostics, item)
        if defense:
            arrays['defense_modifiers'] = defense
        arrays['item_data_hex'] = item_data.hex()
        if (
            not arrays['complete']
            or (
                expected_arrays is not None
                and arrays
                != {k: v for k, v in expected_arrays.items() if k not in ('stat_diagnostics', 'socket_items')}
            )
            or not unit_matches(reader.read, item)
        ):
            raise ValueError('Selected item stats changed')
        if describe_item(reader.read, item) != item['details']:
            raise ValueError('Selected item moved')
        if reader.read(item['data_pointer'], 0x60) != item_data:
            raise ValueError('Selected item metadata changed')
        previous_sockets = (expected_arrays or {}).get('socket_items')
        if socket_candidates is None and previous_sockets and 'candidate_units' in previous_sockets:
            socket_candidates = previous_sockets['candidate_units']
        if socket_candidates is not None:
            try:
                sockets = read_socket_items(reader.read, item, socket_candidates)
            except (OSError, ValueError) as exc:
                if previous_sockets and 'children' in previous_sockets:
                    raise ValueError('Socket contents changed or unavailable') from exc
                sockets = {'reason': str(exc)}
            if (
                previous_sockets
                and 'children' in previous_sockets
                and any(sockets.get(key) != previous_sockets.get(key) for key in ('children', 'complete', 'source'))
            ):
                raise ValueError('Socket contents changed')
            arrays['socket_items'] = sockets
        if expected_arrays is None and item['stats_pointer']:
            arrays['stat_diagnostics'] = diagnostics
    finally:
        os.close(fd)
    after = process_mappings(pid)
    if identity(pid) != images['identity'] or any(
        read_mappings(before, a, n) != read_mappings(after, a, n) for a, n in reader.ranges
    ):
        raise ValueError('Selected item process/mapping changed')
    return arrays


class SelectionUnavailable(ValueError):
    def __init__(self, reason, diagnostics):
        super().__init__(reason)
        self.diagnostics = diagnostics


class AppraisalCapture:
    def __init__(self, pid, images, capture, *, reconnect=None):
        self.pid, self.images, self.capture = pid, images, capture
        self.reconnect = reconnect

    def ensure_connected(self):
        if self.reconnect is None:
            return
        try:
            if identity(self.pid) == self.images['identity']:
                return
        except OSError, ValueError:
            pass
        # Replace every process-bound address together, only after build-gated
        # attachment succeeds. A failed attach is retried on the next request.
        self.pid, self.images, self.capture = self.reconnect()

    def sample_selection(self, *, all_grids=False):
        return capture_ui_sample(
            lambda: observe_ui(self.pid, self.images),
            lambda: sample_units(self.pid, self.images, self.capture, merc=True),
            lambda units: observe_ui(self.pid, self.images, units, all_grids=all_grids),
        )

    def selection(self):
        sample = self.sample_selection()
        selection = resolve_selection(sample, self.images['candidate_base'])
        if selection['status'] != 'candidate':
            raise SelectionUnavailable(
                selection.get('reason', 'No inventory item under the mouse'),
                {
                    'validated': False,
                    'initial': sample,
                    'selection': selection,
                    'image_base': self.images['candidate_base'],
                    'captured_at': timestamp(),
                },
            )
        return sample, selection

    def freeze(self):
        started = time.monotonic()
        self.ensure_connected()
        if time.monotonic() - started > 1:
            raise ValueError('Game reconnected; press Alt+D again to capture the current item')
        if not game_focused(self.images):
            raise ValueError('D2R is not focused')
        try:
            sample, selection = self.selection()
        except SelectionUnavailable as exc:
            diagnostics = exc.diagnostics
            mouse = diagnostics['initial'].get('after', {}).get('widgets', {}).get('mouse')
            if diagnostics['selection']['status'] == 'unavailable' and mouse is not None:
                try:
                    if not game_focused(self.images):
                        raise ValueError('Game focus changed before panel discovery')
                    diagnostics['expanded'] = self.sample_selection(all_grids=True)
                except Exception as discovery_error:
                    diagnostics['discovery_error'] = str(discovery_error)
            # Discovery never substitutes a later hover for the requested item.
            raise
        item = selection['item']
        snapshot = sample['snapshot']
        arrays = verify_item(
            self.pid, self.images, item, socket_candidates=snapshot.get('groups', {}).get('items', {}).get('units', [])
        )
        row = {key: copy.deepcopy(item[key]) for key in ('unit_id', 'txt_id', 'mode', 'details')}
        row['resource_stats'] = arrays
        snapshot['resources'] = {'complete': True, 'items': [row], 'selected_only': True}
        report = {
            'state': 'complete',
            'finished_at': timestamp(),
            'game': {'identity': self.images['identity'], 'executable_fingerprint': {'sha256': SUPPORTED_SHA256}},
        }
        observation = selected_observation(
            snapshot,
            report,
            item['unit_id'],
            inventory_page=selection['container']['page'],
            **(
                {'selection_sample': sample, 'image_base': self.images['candidate_base']}
                if selection['container']['page'] in (4, 255) or selection.get('owner_type') == 1
                else {}
            ),
        )
        rows = [r for r in snapshot['resources']['items'] if r['unit_id'] == item['unit_id']]
        verify_item(self.pid, self.images, item, rows[0]['resource_stats'])
        if not game_focused(self.images):
            raise ValueError('Game focus changed during capture')
        if time.monotonic() - started > 1:
            raise ValueError('Capture exceeded the one-second request window')
        return {
            'observation': observation,
            'selection': selection,
            'sample': sample,
            'arrays': rows[0]['resource_stats'],
            'identity': self.images['identity'],
            'captured_at': timestamp(),
            'capture_ms': round((time.monotonic() - started) * 1000, 2),
        }

    def still_selected(self, frozen):
        # Publication must never reconnect or accept an old process's capture.
        if self.images['identity'] != frozen['identity']:
            return False
        try:
            if identity(self.pid) != frozen['identity'] or not game_focused(self.images):
                return False
        except OSError, ValueError:
            return False
        sample, selection = self.selection()
        original = frozen['selection']['item']
        current = selection['item']
        if any(selection.get(k) != frozen['selection'].get(k) for k in ('owner_id', 'owner_type', 'container')):
            return False
        if any(current[k] != original[k] for k in ('address', 'unit_id', 'data_pointer', 'stats_pointer', 'details')):
            return False
        sample_record: Any = sample
        expected_viewer = frozen.get('observation', {}).get('source', {}).get('viewer_context')
        if expected_viewer and viewer_context((sample_record or {}).get('snapshot', {})) != expected_viewer:
            return False
        candidates = (sample_record or {}).get('snapshot', {}).get('groups', {}).get('items', {}).get('units')
        verify_item(self.pid, self.images, original, frozen['arrays'], socket_candidates=candidates)
        return game_focused(self.images)
