#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
IMAGE=measure-notification-fatigue
NAME=measure-notification-fatigue-run
docker build -q -t "$IMAGE" "$ROOT/task/environment" >/dev/null
docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --name "$NAME" "$IMAGE" >/dev/null
docker cp "$ROOT/task/solution"/. "$NAME:/solution"
docker exec "$NAME" sh /solution/solve.sh
docker cp "$ROOT/task/tests"/. "$NAME:/tests"
docker exec "$NAME" sh /tests/test.sh
docker exec "$NAME" cat /app/reward.txt
docker rm -f "$NAME" >/dev/null

