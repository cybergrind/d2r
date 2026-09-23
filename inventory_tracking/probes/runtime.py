"""High-level host diagnostic workflow."""

import json

from inventory_tracking.common import LOG, error, log_to_file, timestamp
from inventory_tracking.native.capture_probe import capture_image
from inventory_tracking.native.image_probe import inspect_images
from inventory_tracking.native.layout import SUPPORTED_SHA256
from inventory_tracking.native.session import inspect_game, reader_environment, select_game_process
from inventory_tracking.native.unit_probe import inspect_units
from inventory_tracking.reports import create_run, publish


def run_diagnostics(
    report,
    requested_pid,
    images=False,
    capture_directory=None,
    units=False,
    merc=False,
    resources=False,
    item_class=None,
):
    try:
        report.update(reader_environment())
        pid = select_game_process(requested_pid)
        report['game'] = inspect_game(pid)
        if (
            item_class is not None
            and report['game'].get('executable_fingerprint', {}).get('sha256') != SUPPORTED_SHA256
        ):
            raise ValueError('Unsupported game build for item-stat probe')
        access = report['game'].get('memory_access', False)
        if images and access:
            report['images'] = inspect_images(pid, report['game'])
            LOG.info('Image discovery: %s', json.dumps(report['images']))
            access = report['images']['status'] == 'candidate'
        if capture_directory is not None and access:
            report['capture'] = capture_image(pid, report['images'], capture_directory)
            access = report['capture']['status'] == 'captured' and report['capture']['bytes_read'] > 0
        if units and access:
            report['units'] = inspect_units(
                pid,
                report['images'],
                report['capture'],
                capture_directory,
                merc=merc,
                **({'resources': True} if resources else {}),
                **({'item_class': item_class} if item_class is not None else {}),
            )
            access = report['units']['status'] == 'research' and report['units']['complete']
        report['state'] = 'complete' if access else 'blocked'
        report['exit_code'] = 0 if access else 2
        LOG.info('Game diagnostic result: %s', json.dumps(report['game']))
    except (Exception, KeyboardInterrupt) as exc:
        report.update(state='failed', error=error(exc), exit_code=1)
        LOG.exception('Probe failed')
    report['finished_at'] = timestamp()
    LOG.info('Finished: state=%s exit_code=%s', report['state'], report['exit_code'])


def probe(args):
    directory, report = create_run(args.output)
    with log_to_file(directory / 'probe.log'):
        publish(directory / 'report.json', report)
        LOG.info('Started run %s; output %s', report['run_id'], directory)
        resources = getattr(args, 'resources', False)
        item_class = getattr(args, 'item_class', None)
        units = args.units or args.merc or resources or item_class is not None
        capture = args.capture or units
        run_diagnostics(
            report,
            args.pid,
            args.images or capture,
            directory if capture else None,
            units,
            args.merc,
            resources,
            item_class,
        )
        publish(directory / 'report.json', report)
    return report['exit_code']
