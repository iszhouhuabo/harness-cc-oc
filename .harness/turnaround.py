from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _seconds(started: str | None, completed: str | None) -> float | None:
    if not started or not completed:
        return None
    try:
        return max(0.0, (datetime.fromisoformat(completed) - datetime.fromisoformat(started)).total_seconds())
    except ValueError:
        return None


def _agent_id(payload: dict[str, object]) -> str:
    return str(payload.get("agent_id") or payload.get("agentId") or "unknown")


def _conclusion(preflight: dict[str, object]) -> str | None:
    values = {
        str(item.get("conclusion"))
        for item in preflight.get("artifacts", [])
        if isinstance(item, dict) and item.get("conclusion")
    }
    return next(iter(values)) if len(values) == 1 else ("MIXED" if values else None)


def summarize(harness_root: Path, task: str) -> dict[str, object]:
    ledger = _load(harness_root / ".turnaround" / f"{task}.json", {"calls": []})
    calls = ledger.get("calls", []) if isinstance(ledger, dict) else []
    calls = [item for item in calls if isinstance(item, dict)]
    durations = [float(item["active_seconds"]) for item in calls if isinstance(item.get("active_seconds"), (int, float))]
    starts = [str(item["started_at"]) for item in calls if item.get("started_at")]
    stops = [str(item["completed_at"]) for item in calls if item.get("completed_at")]
    by_role: dict[str, int] = {}
    stage_first: dict[str, bool] = {}
    for item in calls:
        role, stage = str(item.get("role") or "unknown"), str(item.get("stage") or "unknown")
        by_role[role] = by_role.get(role, 0) + 1
        stage_first.setdefault(stage, item.get("attempt") == 1 and item.get("conclusion") == "PASS")
    wall = _seconds(min(starts) if starts else None, max(stops) if stops else None)
    complete = len(durations) == len(calls) and bool(calls)
    return {
        "version": 1, "task": task, "generated_at": _now(), "call_count": len(calls),
        "calls_by_role": by_role, "worker_active_seconds": round(sum(durations), 3) if complete else None,
        "lifecycle_wall_seconds": round(wall, 3) if complete and wall is not None else None,
        "timing_complete": complete, "incomplete_call_count": len(calls) - len(durations),
        "first_pass": {
            "passed": sum(stage_first.values()), "total": len(stage_first),
            "rate": round(sum(stage_first.values()) / len(stage_first), 4) if stage_first else None,
        },
        "calls": calls,
    }


def observe(
    harness_root: Path, payload: dict[str, object], *, event: str, platform: str,
    role: str, task: str | None = None, stage: str | None = None,
    preflight: dict[str, object] | None = None,
) -> dict[str, object]:
    agent_id = _agent_id(payload)
    active_path = harness_root / ".turnaround" / "active" / f"{agent_id}.json"
    if event == "start":
        active = {"agent_id": agent_id, "platform": platform, "role": role, "started_at": _now(), "preflight_failures": []}
        _write(active_path, active)
        return {"recorded": "start", **active}
    active = _load(active_path, {})
    if not isinstance(active, dict):
        active = {}
    active.update({"agent_id": agent_id, "platform": platform, "role": role})
    if preflight and preflight.get("verdict") != "PASS":
        failures = active.setdefault("preflight_failures", [])
        if isinstance(failures, list):
            failures.append({"at": _now(), "issues": preflight.get("issues", [])})
        if task:
            active["task"] = task
        _write(active_path, active)
        return {"recorded": "preflight_block", "agent_id": agent_id, "task": task}
    completed_at = _now()
    call = {
        "agent_id": agent_id, "platform": platform, "role": role, "stage": stage,
        "started_at": active.get("started_at"), "completed_at": completed_at,
        "active_seconds": _seconds(active.get("started_at"), completed_at),
        "preflight_failure_count": len(active.get("preflight_failures", [])),
        "conclusion": _conclusion(preflight or {}),
    }
    if not task:
        return {"recorded": "incomplete", "call": call}
    ledger_path = harness_root / ".turnaround" / f"{task}.json"
    ledger = _load(ledger_path, {"version": 1, "task": task, "calls": []})
    calls = ledger.setdefault("calls", [])
    prior = [item for item in calls if isinstance(item, dict) and item.get("role") == role and item.get("stage") == stage]
    call["attempt"] = len(prior) + 1
    calls.append(call)
    _write(ledger_path, ledger)
    try:
        active_path.unlink()
    except FileNotFoundError:
        pass
    summary = summarize(harness_root, task)
    _write(harness_root / ".hook-results" / f"{task}--turnaround.json", summary)
    return summary
