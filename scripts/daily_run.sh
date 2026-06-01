#!/bin/bash
# Backward compatibility wrapper delegating to root daily_run.sh
cd "$(dirname "$0")/.."
./daily_run.sh "$@"
