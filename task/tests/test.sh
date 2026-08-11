#!/bin/sh
set -eu
cd /tests
if pytest -q; then printf '1\n' > /app/reward.txt; else printf '0\n' > /app/reward.txt; exit 1; fi

