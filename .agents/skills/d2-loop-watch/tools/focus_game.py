"""Focus the single D2R window through niri, verifying compositor state afterward."""

import json
import subprocess


APP_ID = 'steam_app_2536520'


def windows():
    result = subprocess.run(['niri', 'msg', '--json', 'windows'], capture_output=True, text=True, check=True, timeout=5)
    return [window for window in json.loads(result.stdout) if window.get('app_id') == APP_ID]


def main():
    candidates = windows()
    if len(candidates) != 1 or candidates[0].get('title') != 'Diablo II: Resurrected':
        raise SystemExit('Expected exactly one identified Diablo II window; focus unchanged')
    window = candidates[0]
    if not window['is_focused']:
        subprocess.run(['niri', 'msg', 'action', 'focus-window', '--id', str(window['id'])], check=True, timeout=5)
    if not any(w['id'] == window['id'] and w['is_focused'] for w in windows()):
        raise SystemExit('Diablo II focus was not confirmed')
    print('Diablo II focus confirmed')


if __name__ == '__main__':
    main()
