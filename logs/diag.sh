#!/usr/bin/env bash
set -e
cd /home/yugaaank/Projects/needle
echo "=== uv pip dry-run verbose, grep entry/conflict ==="
uv pip install --dry-run /home/yugaaank/Projects/needle --python /tmp/colltest/bin/python -v 2>&1 | grep -iE "entry|needle|conflict|duplicate|collision|console|script" | head -30
echo "=== show both packages entry_points.txt ==="
PY=/tmp/colltest/bin/python
$PY -c "
import importlib.metadata as m
for dist in ['cactus-needle','needle-mcp']:
    try:
        eps = m.entry_points(group='console_scripts')
        sel = [e for e in eps if e.name=='needle']
        print(dist, '->', [(e.value) for e in sel])
    except Exception as e:
        print(dist, 'ERR', e)
"
