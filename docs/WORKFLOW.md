# Operational Workflows

This guide outlines the standard procedures for running and maintaining the Smart Stock Selector system.

## 1. Daily Routine (Automated)

The most common operation is the daily data sync and score recalculation.

**Command:**

```cmd
daily_run.bat
```

**What it does:**

1. **Sync**: Fetches latest OHLCV data for 1000+ TWSE stocks (`backend/main.py --sync`).
2. **Recalc**: Uses the existing AI model to compute V2 Indicators, Rise Scores, and new predictions for all stocks (`backend/recalculate.py`).

## 2. Manual Operations

### A. Sync Data Only

To fetch the latest prices without triggering a full recalc (useful for intraday checks):

```bash
python backend/main.py --sync
```

### B. Force Recalculation

If you changed the scoring logic in `core/rise_score_v2.py` and want to update all existing stocks:

```bash
python backend/recalculate.py
```

### C. Model Retraining (Ad-hoc)

When strategy rules change or you want the model to absorb new market data, manually retrain:

```bash
python backend/train_ai.py
```

This generates a versioned `.pkl` file and a performance scorecard in `models_history.json`.

### D. Model Lifecycle Management

The system tracks all trained models in `models_history.json`. You can manage versions using `backend/manage_models.py`:

```bash
# View model leaderboard with performance scores
python backend/manage_models.py list

# Swap to a better performing historical model
python backend/manage_models.py activate <version_string>

# Clean up low-performing models (keep top 5)
python backend/manage_models.py prune --keep=5
```

> [!TIP]
> After using `activate` to swap a model, you MUST restart the backend server for the change to take effect in the live API.

### E. Updating Strategy Parameters

If you modify any AI strategy parameters (e.g., `TARGET_GAIN`, `STOP_LOSS`, `MIN_TRAIN_ROWS`) in `core/config.py`:

> [!WARNING]
> You **MUST** complete two manual steps for the changes to take effect:
>
> 1. **Retrain the Model**: Run `python -c "from core.ai.trainer import train_and_save; from core.data import load_all; train_and_save(load_all())"` (or trigger a sync if data changed) to generate a new `model_sniper.pkl`.
> 2. **Restart the Backend**: If `python backend/main.py` is currently running, you MUST terminate it (Ctrl+C) and restart it so it can load the new code and the new model into memory.

## 3. Frontend Development

To start the React development server:

```bash
cd frontend/v4
npm run dev
```

The frontend will be available at `http://localhost:5173`.
Ensure the backend is running on `http://localhost:8000` for API calls to work.

## 4. Production Deployment

To serve the app in production mode:

1. **Build Frontend**:

    ```bash
    cd frontend/v4
    npm run build
    ```

    This creates static assets in `frontend/v4/dist`.

2. **Start Backend**:

    ```bash
    python backend/main.py
    ```

    The FastAPI server is configured to serve the static files from `frontend/v4/dist` at the root URL `/`.

## 5. AI-Assisted Development (Superpowers)

Our development process utilizes the **Superpowers** framework for high-quality, AI-collaborative engineering.

### Workflow Steps

1. **`/bootstrap`**: Initialize the task by providing the Agent with all necessary project context, constraints, and current file states.
2. **`/plan`**: Before any implementation, the Agent must produce a detailed execution plan (`implementation_plan.md`) for human review.
3. **`/implement`**: Once the plan is approved, the Agent executes the changes in small, reversible steps.
4. **`/review`**: Perform automated and manual reviews to ensure alignment with the **Engineering Constitution**.
5. **`/test`**: Validate changes against the [Testing Protocol](TESTING_PROTOCOL.md) before final completion.

## 6. Logging & Troubleshooting

- Core runtime paths should use structured logger outputs (`core.logger`) instead of ad-hoc `print` so logs can be filtered by level and source.
- **Info**: schema migrations, lifecycle milestones.
- **Warning**: retryable remote fetch failures or degraded fallbacks.
- **Error/Exception**: DB write failures, exhausted retries, and unhandled process failures.
- During incident triage, inspect backend logs first, then reproduce with narrow-scope API calls (`/api/sync/status`, `/api/v4/sniper/candidates`, `/api/v4/stock/{ticker}`).
