#!/usr/bin/env bash
# Pull the latest bridge image and restart. Idempotent — safe to run on a timer.
#
# Usage: run on the deployment host from the repo root.
#   ./deploy/deploy.sh
#
# Assumes deploy/.env exists with the required settings (see .env.example).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Keep the repo's deploy artifacts current, but don't clobber uncommitted
# changes on the host (e.g. Caddyfile tweaks).
git fetch --quiet origin main
git reset --hard origin/main

cd deploy

COMPOSE=(docker compose -f docker-compose.prod.yml --env-file .env)

"${COMPOSE[@]}" pull
"${COMPOSE[@]}" up -d --remove-orphans
"${COMPOSE[@]}" ps

# Prune dangling images to keep disk usage sane on the small EC2 box.
docker image prune -f > /dev/null

echo "✓ bridge deploy complete"
