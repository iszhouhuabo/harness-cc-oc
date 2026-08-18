from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from harness import HARNESS, ROOT, decode_output, now, run_worker_preflight, write_json
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from turnaround import observe  # noqa: E402


ROLE_ALIASES = {
    "ba": "business-analyst", "business-analyst": "business-analyst",
    "sa": "solution-architect", "solution-architect": "solution-architect",
    "rr": "readiness-reviewer", "readiness-reviewer": "readiness-reviewer",
    "dev": "developer", "developer": "developer",
    "cr": "code-reviewer", "code-reviewer": "code-reviewer",
    "te": "test-engineer", "test-engineer": "test-engineer", "test_engineer": "test-engineer",
}


def read_payload() -> dict[str, object]:
    try:
        raw = sys.stdin.read()
        value = json.loads(raw) if raw.strip() else {}
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def text_payload(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def infer_task(payload: dict[str, object]) -> str | None:
    text = text_payload(payload)
    patterns = (
        r"TASK_NAME\s*[:=]\s*([a-z0-9][a-z0-9_-]*)",
        r"harness[/\\]specs[/\\]([a-z0-9][a-z0-9_-]*)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def infer_role(payload: dict[str, object]) -> str | None:
    text = text_payload(payload).lower()
    matches = {
        role
        for alias, role in ROLE_ALIASES.items()
        if re.search(rf"(?<![a-z0-9_-]){re.escape(alias)}(?![a-z0-9_-])", text)
    }
    return next(iter(matches)) if len(matches) == 1 else None


def infer_stage(payload: dict[str, object], role: str | None) -> str | None:
    text = text_payload(payload).lower()
    if role == "solution-architect" and re.search(r"work_mode\s*[:=]\s*impact[_-]analysis", text):
        return "impact-analysis"
    return {
        "business-analyst": "requirements", "solution-architect": "design",
        "readiness-reviewer": "readiness", "developer": "development",
        "code-reviewer": "review", "test-engineer": "testing",
    }.get(role or "")


def main() -> int:
    parser = argparse.ArgumentParser(description="Worker stop preflight and fail-open delivery dispatcher.")
    parser.add_argument("--platform", default="unknown")
    parser.add_argument("--role", choices=tuple(dict.fromkeys(ROLE_ALIASES.values())))
    parser.add_argument("--task")
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--event", choices=("start", "stop"), default="stop")
    args = parser.parse_args()
    payload = read_payload()
    role = args.role or infer_role(payload)
    task = args.task or infer_task(payload)
    stage = infer_stage(payload, role)
    if args.event == "start" and role in ROLE_ALIASES.values():
        observe(HARNESS, payload, event="start", platform=args.platform, role=role)
        print(json.dumps({"suppressOutput": True}, ensure_ascii=False))
        return 0
    audit = {
        "at": now(),
        "platform": args.platform,
        "role": role,
        "task": task,
        "stage": stage,
        "action": "preflight",
    }
    if role not in ROLE_ALIASES.values() or not task or not stage:
        write_json(HARNESS / ".hook-results" / "last-audit.json", audit)
        print(json.dumps({"suppressOutput": True}, ensure_ascii=False))
        return 0

    preflight = run_worker_preflight(task, role, stage)
    write_json(HARNESS / ".hook-results" / f"{task}--{role}--preflight.json", preflight)
    if preflight["verdict"] != "PASS":
        observe(HARNESS, payload, event="stop", platform=args.platform, role=role, task=task, stage=stage, preflight=preflight)
        if not args.audit_only:
            reason = preflight["summary"] + "\n- " + "\n- ".join(preflight["issues"])
            print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
            return 0
        observe(HARNESS, payload, event="stop", platform=args.platform, role=role, task=task, stage=stage)
    else:
        observe(HARNESS, payload, event="stop", platform=args.platform, role=role, task=task, stage=stage, preflight=preflight)

    if role in {"developer", "test-engineer"} and not args.audit_only:
        command = [sys.executable, str(HARNESS / "scripts" / "harness.py"), "delivery", task, "--role", role, "--write-result"]
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, check=False)
        audit["delivery_exit_code"] = completed.returncode
        audit["delivery_output"] = decode_output(completed.stdout).strip()
    write_json(HARNESS / ".hook-results" / "last-audit.json", audit)
    # Mechanical preflight is the only blocking decision. Delivery evidence transport remains fail-open.
    print(json.dumps({"suppressOutput": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
