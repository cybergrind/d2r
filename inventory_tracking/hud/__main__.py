"""Run the HUD canvas: uv run -m inventory_tracking.hud [--scene DIR]. Exits quietly if one already runs."""

import argparse
from pathlib import Path

from inventory_tracking.common import LOG, configure_logging
from inventory_tracking.hud.process import acquire_instance
from inventory_tracking.hud.scene import DEFAULT_SCENE


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene', type=Path, default=DEFAULT_SCENE, help='scene directory producers publish into')
    args = parser.parse_args(argv)
    configure_logging()
    instance = acquire_instance(args.scene)
    if instance is None:
        LOG.info('A HUD canvas already runs for %s', args.scene)
        return 0
    with instance:
        from inventory_tracking.hud import canvas

        return canvas.run(args.scene)


if __name__ == '__main__':
    raise SystemExit(main())
