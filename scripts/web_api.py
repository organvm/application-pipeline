#!/usr/bin/env python3
"""Conductor — REST API + dashboard backend for the application pipeline.

This is the *product surface* layer: it exposes the same clean ``pipeline_api``
functions that back the MCP server (``mcp_server.py``) over HTTP, and serves a
zero-build dashboard SPA from ``scripts/web/``. Continues the "surfacing"
principle — every internal process gets an external surface.

Surfaces built on this module:
  - REST API + auto OpenAPI docs at ``/docs`` (this file)
  - Dashboard UI served at ``/`` (scripts/web/)
  - MCP server (scripts/mcp_server.py)
  - ACP agent server (scripts/acp_server.py)

FastAPI is an *optional* dependency (``pip install -e ".[web]"``). The module
imports without it so module-discovery and non-web tooling never break; the app
is only constructed inside :func:`create_app`.

Safety: mutating endpoints (score/advance) run in dry-run mode by default.
Real writes require the environment flag ``CONDUCTOR_ALLOW_WRITES=1`` — the
hook a hosted, authenticated deployment would gate behind a paid plan.

Run locally:
    pip install -e ".[web]"
    uvicorn scripts.web_api:app --reload
    # or: python scripts/run.py serve
"""

from __future__ import annotations

import dataclasses
import os
from enum import Enum
from pathlib import Path
from typing import Any

try:  # Prefer package-style imports when available.
    from . import pipeline_api as api
    from .conductor_auth import AccountStore, account_public_view, get_billing_provider
    from .pipeline_lib import ALL_PIPELINE_DIRS_WITH_POOL, load_entries, load_entry_by_id
except ImportError:  # pragma: no cover - script execution fallback
    import pipeline_api as api
    from conductor_auth import AccountStore, account_public_view, get_billing_provider
    from pipeline_lib import ALL_PIPELINE_DIRS_WITH_POOL, load_entries, load_entry_by_id

WEB_DIR = Path(__file__).resolve().parent / "web"

# Statuses considered "actionable" for the dashboard pipeline board.
PIPELINE_ORDER = [
    "research",
    "qualified",
    "drafting",
    "staged",
    "deferred",
    "submitted",
    "acknowledged",
    "interview",
    "outcome",
]


def writes_allowed() -> bool:
    """Whether mutating operations may run for real (vs. dry-run only)."""

    return os.environ.get("CONDUCTOR_ALLOW_WRITES", "").strip() in {"1", "true", "yes"}


# --------------------------------------------------------------------------
# Serialization — shared with acp_server.py
# --------------------------------------------------------------------------
def to_jsonable(obj: Any) -> Any:
    """Recursively convert dataclasses / enums / Paths into JSON-safe data."""

    if isinstance(obj, Enum):
        return obj.value
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: to_jsonable(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, Path):
        return str(obj)
    return obj


# --------------------------------------------------------------------------
# Read helpers (power the dashboard)
# --------------------------------------------------------------------------
def _score_of(entry: dict) -> float | None:
    fit = entry.get("fit") or {}
    score = fit.get("score")
    return float(score) if isinstance(score, (int, float)) else None


def entry_summary(entry: dict) -> dict:
    """Project a full pipeline entry down to dashboard/table fields."""

    target = entry.get("target") or {}
    deadline = entry.get("deadline") or {}
    fit = entry.get("fit") or {}
    return {
        "id": entry.get("id"),
        "name": entry.get("name") or entry.get("id"),
        "organization": target.get("organization"),
        "track": entry.get("track"),
        "status": entry.get("status"),
        "score": _score_of(entry),
        "identity_position": fit.get("identity_position"),
        "deadline": deadline.get("date"),
        "deadline_type": deadline.get("type"),
        "url": target.get("application_url") or target.get("url"),
        "dir": entry.get("_dir"),
    }


def list_entry_summaries(status: str | None = None, track: str | None = None) -> list[dict]:
    """Return summarized entries across all pipeline directories, filtered."""

    entries = load_entries(dirs=ALL_PIPELINE_DIRS_WITH_POOL)
    summaries = [entry_summary(e) for e in entries if isinstance(e, dict)]
    if status:
        summaries = [s for s in summaries if s["status"] == status]
    if track:
        summaries = [s for s in summaries if s["track"] == track]
    summaries.sort(key=lambda s: (s["score"] is None, -(s["score"] or 0)))
    return summaries


def pipeline_summary() -> dict:
    """Aggregate KPIs for the dashboard header: counts, scores, distributions."""

    entries = load_entries(dirs=ALL_PIPELINE_DIRS_WITH_POOL)
    by_status: dict[str, int] = {}
    by_track: dict[str, int] = {}
    scores: list[float] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        st = entry.get("status") or "unknown"
        by_status[st] = by_status.get(st, 0) + 1
        tk = entry.get("track") or "unknown"
        by_track[tk] = by_track.get(tk, 0) + 1
        score = _score_of(entry)
        if score is not None:
            scores.append(score)

    actionable = sum(by_status.get(s, 0) for s in ("qualified", "drafting", "staged"))
    submitted = by_status.get("submitted", 0)
    ordered_status = {s: by_status[s] for s in PIPELINE_ORDER if s in by_status}
    # include any non-canonical statuses too
    for s, n in by_status.items():
        ordered_status.setdefault(s, n)

    return {
        "total": sum(by_status.values()),
        "actionable": actionable,
        "submitted": submitted,
        "avg_score": round(sum(scores) / len(scores), 2) if scores else None,
        "scored": len(scores),
        "by_status": ordered_status,
        "by_track": by_track,
        "writes_allowed": writes_allowed(),
    }


# --------------------------------------------------------------------------
# App factory — only touches FastAPI here, so the module imports without it.
# --------------------------------------------------------------------------
def create_app():  # noqa: C901 - cohesive route registration
    """Construct and return the FastAPI application."""

    try:
        from fastapi import Depends, FastAPI, Header, HTTPException, Query
        from fastapi.responses import JSONResponse
        from fastapi.staticfiles import StaticFiles
    except ImportError as exc:  # pragma: no cover - exercised only without extra
        raise RuntimeError(
            "FastAPI is not installed. Install web extras: pip install -e '.[web]'"
        ) from exc

    app = FastAPI(
        title="Conductor — Application Pipeline API",
        version="0.1.0",
        description=(
            "Productized HTTP surface for the application pipeline. Same engine as "
            "the CLI and MCP server. Interactive docs below; dashboard at /."
        ),
    )

    # Account store: built from env. Open mode (anonymous/free) unless an
    # accounts file + CONDUCTOR_AUTH_REQUIRED are configured.
    store = AccountStore.from_env()

    def ok(obj: Any):
        return JSONResponse(to_jsonable(obj))

    def current_account(
        x_api_key: str | None = Header(default=None),
        authorization: str | None = Header(default=None),
    ):
        """Resolve and authorize the calling account; enforce quota."""

        key = x_api_key
        if not key and authorization and authorization.lower().startswith("bearer "):
            key = authorization.split(" ", 1)[1].strip()
        account, error = store.resolve_request(key)
        if error == "unauthorized":
            raise HTTPException(status_code=401, detail="invalid or missing API key")
        if error == "rate_limited":
            raise HTTPException(status_code=429, detail="rate limit exceeded for plan")
        return account

    # ---- Health ----------------------------------------------------------
    @app.get("/api/health", tags=["meta"])
    def health():
        return {
            "status": "ok",
            "service": "conductor",
            "writes_allowed": writes_allowed(),
            "auth_required": store.auth_required,
        }

    @app.get("/api/account", tags=["meta"])
    def account_info(account=Depends(current_account)):
        view = account_public_view(account)
        view["checkout_url"] = get_billing_provider().checkout_url(account.id, account.tier)
        return ok(view)

    # ---- Read: pipeline state -------------------------------------------
    @app.get("/api/summary", tags=["pipeline"])
    def summary():
        return ok(pipeline_summary())

    @app.get("/api/entries", tags=["pipeline"])
    def entries(
        status: str | None = Query(default=None),
        track: str | None = Query(default=None),
    ):
        return ok(list_entry_summaries(status=status, track=track))

    @app.get("/api/entries/{entry_id}", tags=["pipeline"])
    def entry_detail(entry_id: str):
        _, data = load_entry_by_id(entry_id)
        if not data:
            raise HTTPException(status_code=404, detail=f"entry '{entry_id}' not found")
        return ok(data)

    # ---- Read: operational views ----------------------------------------
    @app.get("/api/standup", tags=["ops"])
    def standup(hours: float = 3.0, section: str | None = None):
        return ok(api.standup_data(hours=hours, section=section))

    @app.get("/api/followups", tags=["ops"])
    def followups(entry_id: str | None = None):
        return ok(api.followup_data(entry_id=entry_id))

    @app.get("/api/hygiene", tags=["ops"])
    def hygiene(entry_id: str | None = None):
        return ok(api.hygiene_check(entry_id=entry_id))

    @app.get("/api/triage", tags=["ops"])
    def triage(min_score: float = 9.0):
        return ok(api.triage_data(min_score=min_score, dry_run=True))

    # ---- Write: state machine (persisted only if the account's plan allows) --
    def _may_write(account) -> bool:
        return account.can_write(legacy_flag=writes_allowed())

    @app.post("/api/entries/{entry_id}/score", tags=["actions"])
    def score(entry_id: str, dry_run: bool = True, account=Depends(current_account)):
        effective_dry = dry_run or not _may_write(account)
        return ok(api.score_entry(entry_id=entry_id, dry_run=effective_dry))

    @app.post("/api/entries/{entry_id}/advance", tags=["actions"])
    def advance(entry_id: str, to_status: str | None = None, dry_run: bool = True, account=Depends(current_account)):
        effective_dry = dry_run or not _may_write(account)
        return ok(api.advance_entry(entry_id=entry_id, to_status=to_status, dry_run=effective_dry))

    @app.post("/api/entries/{entry_id}/validate", tags=["actions"])
    def validate(entry_id: str, account=Depends(current_account)):
        return ok(api.validate_entry(entry_id=entry_id))

    @app.post("/api/entries/{entry_id}/submit", tags=["actions"])
    def submit(entry_id: str, account=Depends(current_account)):
        return ok(api.submit_entry(entry_id=entry_id, dry_run=True))

    # ---- Dashboard SPA (mounted last so /api/* wins) ---------------------
    if WEB_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="dashboard")

    return app


# Lazily-created module-level app for `uvicorn scripts.web_api:app`.
class _LazyApp:
    """Defers create_app() until first ASGI call so import never needs FastAPI."""

    def __init__(self) -> None:
        self._app = None

    def _ensure(self):
        if self._app is None:
            self._app = create_app()
        return self._app

    async def __call__(self, scope, receive, send):  # pragma: no cover - ASGI glue
        await self._ensure()(scope, receive, send)


app = _LazyApp()


def main() -> int:
    """Run the dev server (used by `python scripts/run.py serve`)."""

    try:
        import uvicorn
    except ImportError:
        print("uvicorn not installed. Run: pip install -e '.[web]'")
        return 1
    host = os.environ.get("CONDUCTOR_HOST", "127.0.0.1")
    port = int(os.environ.get("CONDUCTOR_PORT", "8000"))
    print(f"Conductor API + dashboard → http://{host}:{port}  (docs: /docs)")
    uvicorn.run(create_app(), host=host, port=port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
