import concurrent.futures
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from backend.backtest import run_time_machine
from backend.limiter import limiter
from backend.repositories.strategy_repo import (
    StrategyNameConflictError,
    StrategyRepository,
)
from core.logger import setup_logger

router = APIRouter()
logger = setup_logger("backend.strategies")

strategy_repo = StrategyRepository()

# Rate limit tiers (per-IP, per-minute). Compare is stricter than backtest's
# 20/minute since each call runs up to 4x the backtest work.
_RATE_STRATEGY = "30/minute"
_RATE_COMPARE = "5/minute"

_MAX_COMPARE_IDS = 4
_COMPARE_TIMEOUT_SECONDS = 30


class StrategyParams(BaseModel):
    """Mirrors GET /api/backtest's exact validation bounds (docs/specs/strategy-lab.md AC2).

    All 7 fields are REQUIRED (no defaults) so a saved strategy is always a
    complete, reproducible bundle — spec AC2 explicitly requires rejecting
    missing keys, not silently filling in /api/backtest's defaults.
    """

    model_config = ConfigDict(extra="forbid")

    target_gain: float = Field(..., ge=0.01, le=0.50, allow_inf_nan=False)
    stop_loss: float = Field(..., ge=0.01, le=0.50, allow_inf_nan=False)
    holding_days: int = Field(..., ge=1, le=90)
    commission_rate: float = Field(..., ge=0.0, le=0.05, allow_inf_nan=False)
    tax_rate: float = Field(..., ge=0.0, le=0.05, allow_inf_nan=False)
    slippage_rate: float = Field(..., ge=0.0, le=0.05, allow_inf_nan=False)
    days_ago: int = Field(..., ge=1, le=365)


class StrategyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    params: StrategyParams
    notes: Optional[str] = None

    @property
    def clean_name(self) -> str:
        return self.name.strip()


class StrategyPatch(BaseModel):
    """Partial update for PUT. Any field omitted is left unchanged; params, if
    provided, must still be a FULL valid StrategyParams bundle (partial-field
    param patches are not supported — the whole params object is replaced then
    re-validated as part of the merged record)."""

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(None, min_length=1)
    params: Optional[StrategyParams] = None
    notes: Optional[str] = None


def _validate_name(name: str) -> str:
    name = name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="name must not be empty")
    return name


@router.get("/api/strategies")
@limiter.limit(_RATE_STRATEGY)
def list_strategies(request: Request):
    try:
        return strategy_repo.list_all()
    except Exception as e:
        logger.error("List strategies error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/api/strategies")
@limiter.limit(_RATE_STRATEGY)
def create_strategy(request: Request, body: StrategyIn):
    name = _validate_name(body.name)
    try:
        return strategy_repo.create(name=name, params=body.params.model_dump(), notes=body.notes)
    except StrategyNameConflictError:
        raise HTTPException(status_code=409, detail="A strategy with this name already exists")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Create strategy error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/api/strategies/{id:int}")
@limiter.limit(_RATE_STRATEGY)
def update_strategy(request: Request, id: int, body: StrategyPatch):
    try:
        existing = strategy_repo.get(id)
        if not existing:
            raise HTTPException(status_code=404, detail="Strategy not found")

        # Merge, then re-validate the WHOLE merged record through StrategyParams —
        # a notes-only edit must never skip params validation (spec AC2).
        merged_params_dict = existing["params"]
        if body.params is not None:
            merged_params_dict = body.params.model_dump()
        try:
            validated_params = StrategyParams(**merged_params_dict)
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid strategy params")

        new_name = existing["name"]
        if body.name is not None:
            new_name = _validate_name(body.name)

        notes_provided = "notes" in body.model_fields_set
        new_notes = body.notes if notes_provided else existing["notes"]

        updated = strategy_repo.update(
            strategy_id=id,
            name=new_name if body.name is not None else None,
            params=validated_params.model_dump(),
            notes=new_notes,
            notes_provided=notes_provided,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Strategy not found")
        return updated
    except StrategyNameConflictError:
        raise HTTPException(status_code=409, detail="A strategy with this name already exists")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Update strategy error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/api/strategies/{id:int}")
@limiter.limit(_RATE_STRATEGY)
def delete_strategy(request: Request, id: int):
    try:
        ok = strategy_repo.delete(id)
        if not ok:
            raise HTTPException(status_code=404, detail="Strategy not found")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Delete strategy error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


def _parse_compare_ids(raw_ids: str) -> list[int]:
    """Server-side validation BEFORE any DB/backtest work (mirrors get_v4_meta)."""
    tokens = [t.strip() for t in raw_ids.split(",")]
    tokens = [t for t in tokens if t != ""]
    if not tokens:
        raise HTTPException(status_code=422, detail="At least one strategy id is required")

    ids: list[int] = []
    for token in tokens:
        if not token.lstrip("-").isdigit():
            raise HTTPException(status_code=422, detail=f"Invalid strategy id: {token!r}")
        ids.append(int(token))

    if len(ids) > _MAX_COMPARE_IDS:
        raise HTTPException(status_code=422, detail=f"Maximum {_MAX_COMPARE_IDS} strategies per comparison")

    if len(set(ids)) != len(ids):
        raise HTTPException(status_code=422, detail="Duplicate strategy ids are not allowed")

    return ids


def _run_one(params: dict[str, Any]) -> dict[str, Any]:
    result = run_time_machine(
        days_ago=params["days_ago"],
        limit=100,
        commission_rate=params["commission_rate"],
        tax_rate=params["tax_rate"],
        slippage_rate=params["slippage_rate"],
        target_gain=params["target_gain"],
        stop_loss=params["stop_loss"],
        holding_days=params["holding_days"],
    )
    return result


@router.get("/api/strategies/compare")
@limiter.limit(_RATE_COMPARE)
def compare_strategies(request: Request, ids: str = Query(..., min_length=1)):
    strategy_ids = _parse_compare_ids(ids)

    strategies: list[dict[str, Any]] = []
    for sid in strategy_ids:
        record = strategy_repo.get(sid)
        if not record:
            raise HTTPException(status_code=404, detail=f"Strategy not found: {sid}")
        strategies.append(record)

    results: list[dict[str, Any]] = []
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=_MAX_COMPARE_IDS) as executor:
            futures = {
                executor.submit(_run_one, s["params"]): s for s in strategies
            }
            future_to_strategy = futures
            pending = dict(futures)
            for future, strategy in future_to_strategy.items():
                try:
                    outcome = future.result(timeout=_COMPARE_TIMEOUT_SECONDS)
                    summary = outcome.get("summary") if isinstance(outcome, dict) else None
                    results.append({
                        "id": strategy["id"],
                        "name": strategy["name"],
                        "summary": summary,
                    })
                except Exception as e:
                    logger.error("Compare backtest failed for strategy %s: %s", strategy["id"], e)
                    results.append({
                        "id": strategy["id"],
                        "name": strategy["name"],
                        "error": "backtest failed for this strategy",
                    })
    except Exception as e:
        logger.error("Compare strategies error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

    # Preserve requested order (as dict submission order can be non-deterministic
    # across worker completion, but here we iterate futures dict which retains
    # insertion order — still, sort explicitly by requested id order for honesty).
    order = {sid: i for i, sid in enumerate(strategy_ids)}
    results.sort(key=lambda r: order.get(r["id"], 0))

    context = strategy_repo.get_history_context()

    return {"context": context, "results": results}
