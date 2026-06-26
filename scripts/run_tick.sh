#!/usr/bin/env bash
# run_tick.sh — Task E2
# Invoked by cron every 5 minutes:
#   */5 * * * * /path/to/run_tick.sh >> /path/to/data/cron.log 2>&1

set -euo pipefail

# Resolve the project root (directory containing this script's parent)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

exec python -m data_layer.runner
