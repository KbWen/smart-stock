"""Model Lifecycle Manager for Smart Stock Selector."""
import sys, os, json, shutil, argparse, glob

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.ai.common import MODEL_PATH, MAX_SAVED_MODELS, select_for_deletion, validate_version_string

_validate_version = validate_version_string  # local alias for CLI readability
_SIDECAR_EXTS = ('.sha256', '.sig')  # integrity sidecar extensions written by trainer

HISTORY_PATH = os.path.join(os.path.dirname(MODEL_PATH), "models_history.json")

def load_history():
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, 'r') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(history):
    import tempfile
    dir_name = os.path.dirname(HISTORY_PATH)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(history, f, indent=2)
        os.replace(tmp_path, HISTORY_PATH)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

def cmd_list():
    """Print all models with their scorecards in a formatted table."""
    history = load_history()
    if not history:
        print("No models found.")
        return
    # Determine active model version
    import joblib
    active_version = "unknown"
    if os.path.exists(MODEL_PATH):
        try:
            data = joblib.load(MODEL_PATH)
            active_version = data.get('version', 'unknown') if isinstance(data, dict) else 'unknown'
        except Exception:
            pass

    print(f"\n{'='*95}")
    # Lift is shown next to precision because precision alone is unreadable: 0.35 against a 14%
    # base rate is an edge, against a 35% base rate it is worse than guessing. `-` means the entry
    # predates the baseline being recorded (2026-09-02), which also means its metrics were
    # produced under the old row-based embargo and are not out-of-sample.
    # `Settle` shows how PF(bt) was measured. "(pre-...)" means the entry predates 2026-09-02,
    # when a winning trade was booked at the session high -- its profit factor is NOT comparable
    # with the others', and rotation refuses to delete it for that reason.
    print(f"{'Version':<25} {'Samples':>8} {'Acc':>6} {'P(SB)':>6} {'Lift':>6} {'R(SB)':>6} {'PF(bt)':>6} {'Settle':>18} {'WR(bt)':>7} {'Active':>7}")
    print(f"{'='*124}")
    for entry in reversed(history):
        v = entry.get('version', '?')
        samples = entry.get('samples', 0)
        oos = entry.get('oos_metrics', {})
        bt = entry.get('backtest_30d', {})
        acc = oos.get('accuracy', '-')
        p2 = oos.get('precision_strong', '-')
        r2 = oos.get('recall_strong', '-')
        lift = oos.get('lift_strong')
        lift = '-' if lift is None else lift
        pf = bt.get('profit_factor', '-')
        settle = bt.get('settlement') or '(pre-2026-09-02)'
        wr = bt.get('win_rate', '-')
        active = " *" if v == active_version else ""
        # Format numeric values
        acc_s = f"{acc:.3f}" if isinstance(acc, (int, float)) else str(acc)
        p2_s = f"{p2:.3f}" if isinstance(p2, (int, float)) else str(p2)
        r2_s = f"{r2:.3f}" if isinstance(r2, (int, float)) else str(r2)
        lift_s = f"{lift:.2f}x" if isinstance(lift, (int, float)) else str(lift)
        pf_s = f"{pf:.2f}" if isinstance(pf, (int, float)) else str(pf)
        wr_s = f"{wr:.1%}" if isinstance(wr, (int, float)) else str(wr)
        print(f"{v:<25} {samples:>8} {acc_s:>6} {p2_s:>6} {lift_s:>6} {r2_s:>6} {pf_s:>6} {settle:>18} {wr_s:>7} {active:>7}")
    print(f"{'='*95}")
    print(f"Active model: {active_version}\n")

def cmd_activate(version):
    """Copy a specific version's .pkl to the main MODEL_PATH atomically."""
    if not _validate_version(version):
        print(f"[ERROR] Invalid version format: {version!r}. Expected: v<N>.<YYYYMMDD>_<HHMM>")
        return
    ts = version.split('.')[-1]
    base_dir = os.path.dirname(MODEL_PATH)
    name_part = os.path.splitext(os.path.basename(MODEL_PATH))[0]
    src = os.path.join(base_dir, f"{name_part}_{ts}.pkl")
    if not os.path.exists(src):
        print(f"[ERROR] Model file not found: {src}")
        return

    import tempfile
    try:
        # Copy and replace sidecars first
        for ext in _SIDECAR_EXTS:
            if os.path.exists(src + ext):
                fd, tmp = tempfile.mkstemp(dir=base_dir, suffix='.tmp')
                os.close(fd)
                shutil.copy2(src + ext, tmp)
                os.replace(tmp, MODEL_PATH + ext)
        # Copy and replace the binary pkl last (atomic switch)
        fd, tmp = tempfile.mkstemp(dir=base_dir, suffix='.tmp')
        os.close(fd)
        shutil.copy2(src, tmp)
        os.replace(tmp, MODEL_PATH)
        print(f"[SUCCESS] Activated model {version} -> {MODEL_PATH}")
    except Exception as e:
        print(f"[ERROR] Failed to activate model atomically: {e}")

def cmd_delete(version):
    """Delete a specific model version."""
    if not _validate_version(version):
        print(f"[ERROR] Invalid version format: {version!r}. Expected: v<N>.<YYYYMMDD>_<HHMM>")
        return
    ts = version.split('.')[-1]
    base_dir = os.path.dirname(MODEL_PATH)
    name_part = os.path.splitext(os.path.basename(MODEL_PATH))[0]
    target = os.path.join(base_dir, f"{name_part}_{ts}.pkl")
    if not os.path.exists(target):
        print(f"[ERROR] Model file not found: {target}")
    else:
        os.remove(target)
        for ext in _SIDECAR_EXTS:
            sidecar = target + ext
            if os.path.exists(sidecar):
                os.remove(sidecar)
        print(f"[DELETED] Deleted model file for {version}")
        
    # Remove from history even if file is missing (cleanup)
    history = load_history()
    new_history = [h for h in history if h.get('version') != version]
    if len(new_history) != len(history):
        save_history(new_history)
        print(f"[CLEANED] Removed {version} from models_history.json")

def cmd_prune(keep=MAX_SAVED_MODELS):
    """Keep the top N COMPARABLE models by profit factor, delete the rest.

    Same irreversible deletion as the trainer's rotation, from a different entry point, so it
    uses the same rule: an entry is eligible for deletion only if its profit factor can be
    compared with the others' -- matching settlement marker, finite value. Anything else is
    protected, even when its profit factor is the lowest present.
    """
    history = load_history()
    if len(history) <= keep:
        print(f"Only {len(history)} models exist, nothing to prune (keep={keep}).")
        return
    to_delete, protected = select_for_deletion(history, keep=keep)
    if protected:
        print(f"[PROTECTED] {len(protected)} model(s) cannot be compared and will NOT be deleted:")
        for h in protected:
            bt = h.get('backtest_30d') or {}
            why = ("no settlement marker (recorded before 2026-09-02)"
                   if not bt.get('settlement') else
                   f"profit_factor unusable (status={bt.get('status', 'unknown')})")
            print(f"           {h.get('version', '?')}: {why}")
        print("           Remove one explicitly with: python backend/manage_models.py delete <version>")
    if not to_delete:
        print(f"Nothing comparable to prune (keep={keep}).")
        return
    for h in to_delete:
        cmd_delete(h['version'])
    print(f"\n[SUCCESS] Pruned {len(to_delete)} comparable models, kept top {keep}.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Model Lifecycle Manager")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("list", help="List all models with scorecards")
    act = sub.add_parser("activate", help="Activate a model version")
    act.add_argument("version", help="Model version tag (e.g., v4.20260225_1343)")
    dl = sub.add_parser("delete", help="Delete a model version")
    dl.add_argument("version", help="Model version tag")
    pr = sub.add_parser("prune", help="Delete low-scoring models")
    pr.add_argument("--keep", type=int, default=MAX_SAVED_MODELS, help="Number of models to keep")

    args = parser.parse_args()
    if args.command == "list": cmd_list()
    elif args.command == "activate": cmd_activate(args.version)
    elif args.command == "delete": cmd_delete(args.version)
    elif args.command == "prune": cmd_prune(args.keep)
    else: parser.print_help()
