"""Model Lifecycle Manager for Smart Stock Selector."""
import sys, os, json, shutil, argparse, glob

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.ai.common import MODEL_PATH, MAX_SAVED_MODELS, profit_factor_sort_key, validate_version_string

_validate_version = validate_version_string  # local alias for CLI readability

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
    with open(HISTORY_PATH, 'w') as f:
        json.dump(history, f, indent=2)

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
    print(f"{'Version':<25} {'Samples':>8} {'Acc':>6} {'P(SB)':>6} {'R(SB)':>6} {'PF(bt)':>6} {'WR(bt)':>7} {'Active':>7}")
    print(f"{'='*95}")
    for entry in reversed(history):
        v = entry.get('version', '?')
        samples = entry.get('samples', 0)
        oos = entry.get('oos_metrics', {})
        bt = entry.get('backtest_30d', {})
        acc = oos.get('accuracy', '-')
        p2 = oos.get('precision_strong', '-')
        r2 = oos.get('recall_strong', '-')
        pf = bt.get('profit_factor', '-')
        wr = bt.get('win_rate', '-')
        active = " *" if v == active_version else ""
        # Format numeric values
        acc_s = f"{acc:.3f}" if isinstance(acc, (int, float)) else str(acc)
        p2_s = f"{p2:.3f}" if isinstance(p2, (int, float)) else str(p2)
        r2_s = f"{r2:.3f}" if isinstance(r2, (int, float)) else str(r2)
        pf_s = f"{pf:.2f}" if isinstance(pf, (int, float)) else str(pf)
        wr_s = f"{wr:.1%}" if isinstance(wr, (int, float)) else str(wr)
        print(f"{v:<25} {samples:>8} {acc_s:>6} {p2_s:>6} {r2_s:>6} {pf_s:>6} {wr_s:>7} {active:>7}")
    print(f"{'='*95}")
    print(f"Active model: {active_version}\n")

def cmd_activate(version):
    """Copy a specific version's .pkl to the main MODEL_PATH."""
    if not _validate_version(version):
        print(f"❌ Invalid version format: {version!r}. Expected: v<N>.<YYYYMMDD>_<HHMM>")
        return
    ts = version.split('.')[-1]
    base_dir = os.path.dirname(MODEL_PATH)
    name_part = os.path.splitext(os.path.basename(MODEL_PATH))[0]
    src = os.path.join(base_dir, f"{name_part}_{ts}.pkl")
    if not os.path.exists(src):
        print(f"❌ Model file not found: {src}")
        return
    shutil.copy(src, MODEL_PATH)
    print(f"✅ Activated model {version} -> {MODEL_PATH}")

def cmd_delete(version):
    """Delete a specific model version."""
    if not _validate_version(version):
        print(f"❌ Invalid version format: {version!r}. Expected: v<N>.<YYYYMMDD>_<HHMM>")
        return
    ts = version.split('.')[-1]
    base_dir = os.path.dirname(MODEL_PATH)
    name_part = os.path.splitext(os.path.basename(MODEL_PATH))[0]
    target = os.path.join(base_dir, f"{name_part}_{ts}.pkl")
    if not os.path.exists(target):
        print(f"❌ Model file not found: {target}")
    else:
        os.remove(target)
        print(f"🗑️ Deleted model file for {version}")
        
    # Remove from history even if file is missing (cleanup)
    history = load_history()
    new_history = [h for h in history if h.get('version') != version]
    if len(new_history) != len(history):
        save_history(new_history)
        print(f"🧹 Removed {version} from models_history.json")

def cmd_prune(keep=MAX_SAVED_MODELS):
    """Keep top N models by profit factor, delete the rest."""
    history = load_history()
    if len(history) <= keep:
        print(f"Only {len(history)} models exist, nothing to prune (keep={keep}).")
        return
    # Sort by profit factor (descending), keep top N.
    # AC2: None profit_factor (backtest failed) ranks below any real score, including 0.0.
    scored = sorted(history, key=profit_factor_sort_key, reverse=True)
    to_keep = set(h['version'] for h in scored[:keep])
    to_delete = [h for h in history if h['version'] not in to_keep]
    for h in to_delete:
        cmd_delete(h['version'])
    print(f"\n✅ Pruned {len(to_delete)} models, kept top {keep}.")

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
