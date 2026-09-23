"""Right-click at the current cursor position every minute. Stop with Ctrl+C."""

import shutil
import subprocess
import time


def main() -> None:
    xdotool = shutil.which('xdotool')
    if xdotool is None:
        raise SystemExit('Install xdotool first. This script requires X11/XWayland.')
    print('Right-click every 60 seconds; first click in 60 seconds. Ctrl+C to stop.', flush=True)
    try:
        while True:
            time.sleep(60)
            subprocess.run([xdotool, 'click', '3'], check=True)
    except KeyboardInterrupt:
        print('\nStopped.')
    except subprocess.CalledProcessError as error:
        raise SystemExit(f'Mouse click failed (exit {error.returncode}).') from error


if __name__ == '__main__':
    main()
