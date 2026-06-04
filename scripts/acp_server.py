#!/usr/bin/env python3
"""Conductor — ACP (Agent Communication Protocol) surface for the pipeline.

Exposes the pipeline as an ACP-compatible agent over HTTP. ACP
(https://agentcommunicationprotocol.dev) is a REST protocol for agent-to-agent
communication: clients discover agents via a manifest endpoint and execute them
by POSTing a run with input *messages* made of typed *parts*.

This is a dependency-light, spec-shaped implementation (manifest + sync runs)
that routes a small natural command grammar to the same ``pipeline_api`` engine
used by the CLI, MCP server, and REST API. It is the fourth product surface
alongside the dashboard UI, REST API, and MCP server.

FastAPI is optional (``pip install -e ".[web]"``); the module imports without
it and the app is built only in :func:`create_app`.

Run locally:
    pip install -e ".[web]"
    uvicorn scripts.acp_server:app --port 8001
    # or: python scripts/run.py acp
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Any

try:  # Prefer package-style imports when available.
    from . import pipeline_api as api
    from .web_api import list_entry_summaries, pipeline_summary, to_jsonable
except ImportError:  # pragma: no cover - script execution fallback
    import pipeline_api as api
    from web_api import list_entry_summaries, pipeline_summary, to_jsonable

AGENT_NAME = "application-pipeline"

AGENT_MANIFEST = {
    "name": AGENT_NAME,
    "description": (
        "Conductor career/grant application pipeline agent. Scores, triages, and "
        "reports on a precision application pipeline. Commands: summary, entries, "
        "standup, followups, hygiene, triage, score <id>, help."
    ),
    "metadata": {
        "programming_language": "Python",
        "natural_languages": ["en"],
        "framework": "conductor",
        "capabilities": [
            "summary",
            "entries",
            "standup",
            "followups",
            "hygiene",
            "triage",
            "score",
        ],
    },
}

# In-memory run store (a hosted deployment would back this with a database).
_RUNS: dict[str, dict] = {}


def _text_part(text: str) -> dict:
    return {"content_type": "text/plain", "content": text}


def _json_part(obj: Any) -> dict:
    return {"content_type": "application/json", "content": json.dumps(to_jsonable(obj))}


def _message(parts: list[dict], role: str = "agent/" + AGENT_NAME) -> dict:
    return {"role": role, "parts": parts}


def extract_text(messages: list[dict]) -> str:
    """Concatenate all text parts from ACP input messages."""

    chunks: list[str] = []
    for msg in messages or []:
        for part in msg.get("parts", []) or []:
            if part.get("content_type", "text/plain").startswith("text/"):
                content = part.get("content")
                if isinstance(content, str):
                    chunks.append(content)
    return " ".join(chunks).strip()


def dispatch(command_text: str) -> list[dict]:
    """Route a command string to the pipeline engine; return ACP output messages."""

    text = (command_text or "").strip()
    lowered = text.lower()
    tokens = lowered.split()
    verb = tokens[0] if tokens else "help"

    if verb in {"summary", "status"}:
        data = pipeline_summary()
        line = (
            f"{data['total']} entries — {data['actionable']} actionable, "
            f"{data['submitted']} submitted, avg score {data['avg_score']}."
        )
        return [_message([_text_part(line), _json_part(data)])]

    if verb in {"entries", "list"}:
        # optional filters: "entries status=staged track=grant"
        filters = dict(t.split("=", 1) for t in tokens[1:] if "=" in t)
        rows = list_entry_summaries(status=filters.get("status"), track=filters.get("track"))
        line = f"{len(rows)} entries" + (f" matching {filters}" if filters else "") + "."
        return [_message([_text_part(line), _json_part(rows)])]

    if verb == "standup":
        result = api.standup_data()
        return [_message([_text_part(result.output or result.error or "(no output)")])]

    if verb in {"followups", "followup"}:
        result = api.followup_data()
        return [_message([_text_part(result.message), _json_part(result.due_actions or [])])]

    if verb == "hygiene":
        result = api.hygiene_check()
        return [_message([_text_part(result.message), _json_part(to_jsonable(result))])]

    if verb == "triage":
        result = api.triage_data(dry_run=True)
        return [_message([_text_part(result.message), _json_part(to_jsonable(result))])]

    if verb == "score":
        if len(tokens) < 2:
            return [_message([_text_part("Usage: score <entry-id>")])]
        # preserve original casing of the id from the raw text
        entry_id = text.split(None, 1)[1].strip()
        result = api.score_entry(entry_id=entry_id, dry_run=True)
        return [_message([_text_part(result.message or result.error or ""), _json_part(to_jsonable(result))])]

    help_text = (
        "Conductor agent commands: summary | entries [status=..] [track=..] | "
        "standup | followups | hygiene | triage | score <id> | help"
    )
    return [_message([_text_part(help_text)])]


def run_agent(messages: list[dict]) -> dict:
    """Execute the agent synchronously and return a completed ACP Run object."""

    run_id = str(uuid.uuid4())
    try:
        output = dispatch(extract_text(messages))
        status = "completed"
        error = None
    except Exception as exc:  # noqa: BLE001 - surface as ACP failed run
        output = []
        status = "failed"
        error = f"{type(exc).__name__}: {exc}"

    run = {
        "run_id": run_id,
        "agent_name": AGENT_NAME,
        "status": status,
        "output": output,
        "error": error,
    }
    _RUNS[run_id] = run
    return run


def create_app():
    """Construct and return the ACP FastAPI application."""

    try:
        from fastapi import Body, FastAPI, HTTPException
    except ImportError as exc:  # pragma: no cover - exercised only without extra
        raise RuntimeError(
            "FastAPI is not installed. Install web extras: pip install -e '.[web]'"
        ) from exc

    app = FastAPI(
        title="Conductor — ACP Agent",
        version="0.1.0",
        description="Agent Communication Protocol surface for the application pipeline.",
    )

    @app.get("/agents", tags=["acp"])
    def list_agents():
        return {"agents": [AGENT_MANIFEST]}

    @app.get("/agents/{name}", tags=["acp"])
    def get_agent(name: str):
        if name != AGENT_NAME:
            raise HTTPException(status_code=404, detail=f"agent '{name}' not found")
        return AGENT_MANIFEST

    @app.post("/runs", tags=["acp"])
    def create_run(body: dict = Body(default=None)):
        body = body or {}
        agent_name = body.get("agent_name", AGENT_NAME)
        if agent_name != AGENT_NAME:
            raise HTTPException(status_code=404, detail=f"agent '{agent_name}' not found")
        messages = body.get("input", [])
        return run_agent(messages)

    @app.get("/runs/{run_id}", tags=["acp"])
    def get_run(run_id: str):
        run = _RUNS.get(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"run '{run_id}' not found")
        return run

    return app


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
    """Run the ACP dev server (used by `python scripts/run.py acp`)."""

    try:
        import uvicorn
    except ImportError:
        print("uvicorn not installed. Run: pip install -e '.[web]'")
        return 1
    host = os.environ.get("CONDUCTOR_HOST", "127.0.0.1")
    port = int(os.environ.get("CONDUCTOR_ACP_PORT", "8001"))
    print(f"Conductor ACP agent → http://{host}:{port}  (manifest: /agents)")
    uvicorn.run(create_app(), host=host, port=port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
