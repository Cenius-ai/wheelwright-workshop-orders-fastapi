#!/usr/bin/env bash
# Stop any workshop server started from this checkout (local development helper).
set -uo pipefail
python3 - <<'PY'
import glob, os, signal

me, parent = os.getpid(), os.getppid()
targets = []
for path in glob.glob('/proc/[0-9]*/cmdline'):
    pid = int(path.split('/')[2])
    if pid in (me, parent):
        continue
    try:
        argv = [p for p in open(path, 'rb').read().decode(errors='replace').split('\x00') if p]
    except OSError:
        continue
    if not argv or not argv[0].endswith('python3'):
        continue
    is_dev_server = (
        len(argv) >= 3 and argv[1] == '-m' and argv[2] == 'uvicorn'
    ) or any(a.endswith('main.py') for a in argv)
    if is_dev_server:
        targets.append((pid, ' '.join(argv)))

for pid, cmd in targets:
    try:
        os.kill(pid, signal.SIGTERM)
        print('stopped', pid, cmd)
    except OSError as exc:
        print('could not stop', pid, exc)
print('no workshop server running' if not targets else f'stopped {len(targets)} server(s)')
PY
