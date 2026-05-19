#!/usr/bin/env bash
# Legacy wrapper — delegates to root test_e2e.sh (14 tests).
exec "$(dirname "$0")/../test_e2e.sh" "$@"
