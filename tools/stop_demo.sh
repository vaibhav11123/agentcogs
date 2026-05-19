#!/usr/bin/env bash
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/demo_daemon.sh"
demo_stop_all
echo "Demo API + dashboard stopped."
