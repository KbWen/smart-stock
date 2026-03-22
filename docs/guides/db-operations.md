# Database Operations Runbook

The app uses **SQLite** (`storage.db`) with three core tables and one indicator cache.

---

## Tables

| Table | Purpose |
|-------|---------|
| `stock_history` | OHLCV price history (one row per ticker per day) |
| `stock_scores` | Latest composite scores + AI probability per ticker |
| `stock_indicators` | Cached technical indicators per ticker |

Schema is auto-initialized in `core/data.py → init_db()` on startup.

---

## Backups

SQLite is a single file. Back it up by copying `storage.db` while the server is stopped (or during low-traffic):

```bash
# Simple copy backup
cp storage.db storage.db.bak.$(date +%Y%m%d_%H%M)

# Or compress
sqlite3 storage.db ".backup storage_$(date +%Y%m%d).db"
```

**Recommended schedule:** daily backup before the morning sync job.

---

## Restore

```bash
# Stop the server first
cp storage.db.bak.YYYYMMDD_HHMM storage.db
# Restart the server
```

---

## Manual Migrations

Migrations are applied inline in `core/data.py → init_db()` using `ALTER TABLE IF NOT EXISTS`. To apply migrations manually in a pinch:

```bash
sqlite3 storage.db
```

Then run the relevant SQL from `init_db()`. Always back up first.

---

## Common Issues

### DB Locked (`database is locked`)

**Cause:** Another process holds a write lock (concurrent sync + API write).

**Fix:**
1. Stop all processes writing to the DB
2. Check for zombie processes: `lsof storage.db` (Linux/Mac) or Task Manager (Windows)
3. Restart the server — SQLite's WAL mode auto-recovers on restart
4. If the lock persists, copy the DB to a new file and restart with the copy:
   ```bash
   sqlite3 storage.db "VACUUM INTO 'storage_clean.db'"
   mv storage_clean.db storage.db
   ```

### DB Corrupt (`database disk image is malformed`)

**Cause:** Power loss during write, or disk error.

**Fix:**
1. Restore from last backup: `cp storage.db.bak.LATEST storage.db`
2. If no backup: attempt recovery:
   ```bash
   sqlite3 broken.db ".recover" | sqlite3 recovered.db
   mv recovered.db storage.db
   ```
3. Re-run the sync job to repopulate missing data

### Missing Data After Restore

Re-run the full sync to repopulate:
```bash
python backend/main.py --sync
# Or trigger via API:
curl -X POST http://localhost:8000/api/sync/trigger
```

### Stock Indicators Out of Date

Recalculate scores and indicators without re-fetching price data:
```bash
python backend/recalculate.py
```

---

## DB Size Management

Each ticker generates ~1 row/day in `stock_history`. With 2,000 TW stocks × 5 years ≈ 3.6M rows ≈ 500 MB.

To trim old history:
```sql
DELETE FROM stock_history WHERE date < '2020-01-01';
VACUUM;
```

---

## Useful SQLite Commands

```bash
# Open DB shell
sqlite3 storage.db

# Check table sizes
SELECT name, COUNT(*) FROM sqlite_master WHERE type='table';
SELECT COUNT(*) FROM stock_history;
SELECT COUNT(*) FROM stock_scores;

# Check last sync time
SELECT MAX(updated_at) FROM stock_scores;

# Find a specific ticker
SELECT * FROM stock_scores WHERE ticker = '2330';

# Vacuum (reclaim space after deletes)
VACUUM;

# WAL checkpoint (flush WAL to main DB)
PRAGMA wal_checkpoint(FULL);
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PATH` | `<repo>/storage.db` | Absolute path to DB file |
| `DB_TIMEOUT` | `30.0` | SQLite busy-timeout (seconds) |

See `docs/guides/environment-setup.md` for full reference.
