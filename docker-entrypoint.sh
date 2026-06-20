#!/bin/sh
# Smart Stock container entrypoint: seed the bundled offline demo, then serve.
#
# On first boot the data volume is empty, so seed_demo loads the bundled demo
# fixture (data/demo/demo_prices.csv) and computes technical scores — fully
# offline, no network. seed_demo is idempotent: it skips the load when the demo
# tickers already exist, so a user's real synced data is never clobbered. No AI
# model is bundled, so AI probability stays N/A until one is trained (honest).
set -e

python scripts/seed_demo.py || echo "[entrypoint] demo seed skipped/failed; continuing to serve"

# exec so the server is PID 1 and receives stop signals cleanly.
exec python backend/main.py
