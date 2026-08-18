from __future__ import annotations

import argparse
import hashlib
import json
import locale
import ntpath
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / ".harness"
SPECS = ROOT / "harness" / "specs"
ARCHIVE = ROOT / "harness" / "archive"
BOARD = ROOT / "harness" / "board.md"
CONTRACT_PATH = HARNESS / "workflow" / "contract.json"
SLUG_RE = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")
ROLE_REPORT = {"developer": "dev-log.md", "test-engineer": "test-report.md"}
ROLE_STAGE = {
    "business-analyst": "requirements", "solution-architect": "design",
    "readiness-reviewer": "readiness", "developer": "development",
    "code-reviewer": "review", "test-engineer": "testing",
}
COMMAND_SECTION = {"developer": "Verification Results", "test-engineer": "Test Matrix"}
BASELINE_IGNORED_PREFIXES = (".harness/", ".opencode/", ".agents/")
EXECUTION_IGNORED_PREFIXES = (*BASELINE_IGNORED_PREFIXES, ".claude/", ".codex/", ".trae/", "harness/")
SHELL_TOKENS = {"&&", "||", "|", ";", "&", ">", "<"}
INVALID_EVIDENCE = {
    "", "-", "--", "---", "—", "–", "n/a", "na", "n.a.", "none", "null",
    "tbd", "todo", "placeholder", "待补", "待填写", "待补充",
}
MAVEN_EXECUTABLES = {"mvn", "mvnw"}
NODE_RUNNERS = {"vitest", "jest", "playwright", "eslint"}
PACKAGE_MANAGERS = {"npm", "pnpm", "yarn", "bun"}
PATH_SUFFIXES = {".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts", ".vue"}
STATUSES = {"PROPOSE", "IN_PROGRESS", "AWAITING_APPLY", "APPLY", "AWAITING_ARCHIVE", "DONE"}
STAGE_RE = re.compile(r"^[a-z][a-z0-9-]*$")
APPLY_REPORTS = {
    "dev-log.md": ("PASS", "Dev"),
    "code-review.md": ("PASS", "CR"),
    "test-report.md": ("PASS", "TE"),
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def decode_output(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    for encoding in dict.fromkeys(("utf-8", locale.getpreferredencoding(False), "gb18030")):
        try:
            return value.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return value.decode("utf-8", errors="replace")


def task_name(value: str) -> str:
    normalized = value.replace("\\", "/").rstrip("/")
    name = normalized.rsplit("/", 1)[-1]
    if not SLUG_RE.fullmatch(name):
        raise ValueError(f"invalid Harness task name: {value!r}")
    return name


def package(value: str, *, archived: bool = False) -> Path:
    return (ARCHIVE if archived else SPECS) / task_name(value)


def conclusion(path: Path) -> str | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    blocks = re.findall(
        r"(?ims)^#{2,3}\s*(?:Conclusion|Result|结论)(?:[^\n]*)\n(.*?)(?=^#{1,3}\s|\Z)", text,
    )
    for block in reversed(blocks):
        for line in block.splitlines():
            value = line.strip().strip("`*_ ")
            if re.fullmatch(r"PASS|BLOCK|REJECT|FAIL", value, flags=re.IGNORECASE):
                return value.upper()
    tail = "\n".join(text.splitlines()[-30:])
    for line in reversed(tail.splitlines()):
        matched = re.match(r"^\s*(?:Conclusion|Result|结论)\s*[:：]\s*(.*?)\s*$", line, re.IGNORECASE)
        if matched:
            value = matched.group(1).strip().strip("`*_ ").upper()
            if value in {"PASS", "BLOCK", "REJECT", "FAIL"}:
                return value
    return None


def load_contract() -> dict[str, object]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def document_format_issues(path: Path, contract: dict[str, object] | None = None, *, strict: bool) -> list[str]:
    active = contract or load_contract()
    documents = active.get("documents", {})
    spec = documents.get(path.name) if isinstance(documents, dict) else None
    if not isinstance(spec, dict) or not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    schema = str(spec.get("schema", ""))
    marker = f"harness-document: {schema}"
    if strict and marker not in text:
        legacy = {"dev-log.md": "dev-log@4", "test-report.md": "test-report@4"}.get(path.name)
        if not legacy or f"harness-document: {legacy}" not in text:
            return [f"{path.name} 缺少 schema 标记 {schema}"]
        marker = f"harness-document: {legacy}"
    if marker not in text:
        return []
    headings = {match.strip() for match in re.findall(r"(?m)^##\s+(.+?)\s*$", text)}
    required = [str(value) for value in spec.get("required_sections", [])]
    if marker.endswith("@4"):
        required = [value for value in required if value != "Verification Inputs"]
    issues = [f"{path.name} 缺少章节：{value}" for value in required if value not in headings]
    if "Conclusion" in required and len(re.findall(r"(?m)^##\s+Conclusion\s*$", text)) != 1:
        issues.append(f"{path.name} 必须且只能包含一个 ## Conclusion")
    checklists = active.get("checklists", {})
    check_ids = checklists.get(path.name, []) if isinstance(checklists, dict) else []
    issues.extend(f"{path.name} 缺少 checklist 行：{value}" for value in check_ids if str(value) not in text)
    return issues


def template_placeholder_issues(path: Path) -> list[str]:
    template = HARNESS / "templates" / "change" / path.name
    if not path.is_file() or not template.is_file():
        return []
    source = re.sub(r"<!--.*?-->", "", template.read_text(encoding="utf-8"), flags=re.DOTALL)
    actual = re.sub(r"<!--.*?-->", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)
    tokens = set(re.findall(r"<[^<>\n]+>", source))
    issues = [f"{path.name} 仍含模板占位符：{token}" for token in sorted(tokens) if token in actual]
    if re.search(r"(?m)^\s*(?:PASS / BLOCK|PASS / REJECT|PASS / FAIL / BLOCK)\s*$", actual):
        issues.append(f"{path.name} 结论仍是模板候选值")
    return issues


def run_worker_preflight(task: str, role: str, stage: str | None = None) -> dict[str, object]:
    name, target, contract = task_name(task), package(task), load_contract()
    active_stage = stage or ROLE_STAGE.get(role)
    stages, roles = contract.get("stages", {}), contract.get("roles", {})
    stage_spec = stages.get(active_stage) if isinstance(stages, dict) else None
    role_spec = roles.get(role) if isinstance(roles, dict) else None
    if not isinstance(stage_spec, dict) or stage_spec.get("role") != role or not isinstance(role_spec, dict):
        raise ValueError(f"role/stage mismatch: {role}/{active_stage}")
    filenames = [str(value) for value in stage_spec.get("documents", [])]
    if role == "business-analyst" and "proposal.md" not in filenames:
        filenames.insert(0, "proposal.md")
    allowed = {str(value) for value in role_spec.get("conclusions", [])}
    artifacts, issues = [], []
    for filename in filenames:
        path = target / filename
        artifact_issues = [f"{filename} 缺失"] if not path.is_file() else [
            *document_format_issues(path, contract, strict=True), *template_placeholder_issues(path),
        ]
        declared = conclusion(path)
        if path.is_file() and declared not in allowed:
            artifact_issues.append(
                f"{filename} 结论必须是 {', '.join(sorted(allowed))}，实际为 {declared or '缺失'}"
            )
        artifacts.append({"path": filename, "conclusion": declared, "issues": artifact_issues})
        issues.extend(artifact_issues)
    return {
        "task": name, "role": role, "stage": active_stage,
        "verdict": "PASS" if not issues else "FAIL", "reason_kind": "owned_report_format",
        "owner": role, "artifacts": artifacts, "issues": issues,
        "next_action": "RETURN_TO_PM" if not issues else "CONTINUE_SAME_WORKER",
        "summary": "owned 产物机械预检通过" if not issues else "owned 产物尚未机械合规；当前 Worker 原地修正后再返回",
    }


def executable(value: str) -> str:
    name = re.split(r"[/\\]", value)[-1].lower()
    return re.sub(r"\.(?:exe|cmd|bat)$", "", name)


def replay_policy_issue(argv: list[str]) -> str | None:
    if not argv:
        return "argv 为空"
    if any(token in SHELL_TOKENS for token in argv):
        return "包含 shell 拼接/重定向；请改成单一 argv 或有限 smoke 脚本"
    name = executable(argv[0])
    if name == "cd" or any(ord(char) > 127 for char in name):
        return "首项不是可执行程序"
    lowered = [value.lower() for value in argv[1:]]
    script = lowered[0] if lowered else ""
    node_script = lowered[1] if len(lowered) >= 2 and script == "run" else script
    if name in PACKAGE_MANAGERS and node_script in {"dev", "start", "serve", "watch"}:
        return "常驻服务命令必须封装为启动、健康检查、停止的有限 smoke 脚本"
    if name == "java" and "-jar" in lowered:
        return "java -jar 属于常驻启动命令"
    if name in MAVEN_EXECUTABLES | {"gradle", "gradlew"} and any(
        value in {"spring-boot:run", "bootrun"} for value in lowered
    ):
        return "框架启动任务属于常驻命令"
    python_server = name.startswith("python") and (
        any(value in {"runserver", "uvicorn", "gunicorn", "hypercorn"} for value in lowered)
        or {"flask", "run"}.issubset(lowered)
    )
    if name in {"uvicorn", "gunicorn", "hypercorn"} or (
        name in {"flask", "django-admin"} and any(value in {"run", "runserver"} for value in lowered)
    ) or python_server:
        return "Python 服务启动命令必须改为有限 smoke 脚本"
    if (name in {"go", "cargo", "dotnet"} and script in {"run", "watch"}) or name == "rackup":
        return "运行/监听任务可能常驻，必须改为有限 smoke 脚本"
    if name in {"rails", "artisan"} and script in {"server", "s", "serve"}:
        return "Web 服务启动命令必须改为有限 smoke 脚本"
    if name in {"bundle", "composer"} and any(value in {"server", "serve", "start"} for value in lowered):
        return "项目服务脚本必须改为有限 smoke 脚本"
    if name == "php" and "-s" in lowered:
        return "PHP 内置服务命令必须改为有限 smoke 脚本"
    return None


def shell_control_tokens(command: str) -> list[str]:
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars="|&;<>")
        lexer.whitespace_split = True
        lexer.commenters = ""
        return [token for token in lexer if token and set(token) <= set("|&;<>")]
    except ValueError:
        return []


def valid_evidence(value: str) -> bool:
    normalized = value.strip().strip("`*_ ")
    return normalized.lower() not in INVALID_EVIDENCE and "<" not in normalized and ">" not in normalized


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence_file_issues(value: str) -> list[str]:
    normalized = value.strip().strip("`*_ ")
    references = []
    if normalized.lower().startswith("file:"):
        references.append(normalized[5:].strip())
    references.extend(re.findall(r"\[[^]]*]\(([^)]+)\)", normalized))
    issues: list[str] = []
    for reference in references:
        if re.match(r"^[a-z][a-z0-9+.-]*://", reference, re.IGNORECASE):
            continue
        raw = reference.split("#", 1)[0].strip().strip("<>")
        candidate = (ROOT / raw).resolve() if not Path(raw).is_absolute() else Path(raw).resolve()
        if candidate != ROOT and ROOT not in candidate.parents:
            issues.append(f"证据文件越出项目：{reference}")
        elif not candidate.is_file():
            issues.append(f"证据文件不存在：{reference}")
        elif candidate.stat().st_size == 0:
            issues.append(f"证据文件为空：{reference}")
    return issues


def command_table_column(value: str) -> str | None:
    normalized = re.sub(r"\s+", " ", value.strip().lower())
    aliases = {
        "command": {"command", "command/steps", "command argv", "command（命令）", "command/命令", "命令", "命令/步骤"},
        "cwd": {"working directory", "working directory/工作目录", "工作目录"},
        "result": {"result", "result/结果", "结果"},
        "exit_code": {"exit code", "exit code/退出码", "退出码"},
        "evidence": {"evidence", "evidence/notes", "evidence/证据", "证据", "证据/备注"},
        "na_reason": {"n/a", "n/a reason", "n/a 理由", "不适用理由"},
        "scope": {"scope", "execution scope", "verification scope", "执行范围", "验证范围"},
    }
    return next((field for field, values in aliases.items() if normalized in values), None)


def markdown_commands(path: Path, role: str) -> tuple[list[tuple[Path, list[str]]], list[str], dict[str, int]]:
    commands: list[tuple[Path, list[str]]] = []
    errors: list[str] = []
    audit = {"rows": 0, "passed": 0, "na": 0}
    columns: dict[str, int] | None = None
    active = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        heading = re.match(r"^##\s+(.+?)\s*$", raw)
        if heading:
            active = heading.group(1).strip().startswith(COMMAND_SECTION[role])
            columns = None
            continue
        if not active:
            continue
        if not raw.lstrip().startswith("|"):
            columns = None
            continue
        cells = [cell.strip().strip("`") for cell in raw.strip().strip("|").split("|")]
        identified = [command_table_column(cell) for cell in cells]
        if "command" in identified and "result" in identified:
            columns = {field: index for index, field in enumerate(identified) if field}
            continue
        if not columns or not {"command", "result"}.issubset(columns) or set("".join(cells)) <= {"-", ":", " "}:
            continue
        command = cells[columns["command"]].strip()
        declared = cells[columns["result"]].strip().strip("`*_ ").upper()
        if declared == "N/A":
            audit["rows"] += 1
            reason = cells[columns["na_reason"]] if "na_reason" in columns and columns["na_reason"] < len(cells) else ""
            if not valid_evidence(reason):
                errors.append(f"N/A 验证行缺少有效 N/A 理由：{command or '空命令'}")
            else:
                audit["na"] += 1
            continue
        if command.lower() in {"command（命令）", "命令", "command", "n/a", "-", ""}:
            if declared == "PASS":
                errors.append("标记 PASS 的验证行缺少可执行命令")
            continue
        if set(command) <= {"-", ":", " "}:
            continue
        if "<" in command or ">" in command or "PASS / FAIL" in command:
            if declared == "PASS":
                errors.append(f"标记 PASS 的验证行仍含命令占位符：{command}")
            continue
        audit["rows"] += 1
        if declared != "PASS":
            errors.append(f"报告包含失败验证行：{command}")
            continue
        exit_code = cells[columns["exit_code"]].strip().strip("`*_ ") if "exit_code" in columns and columns["exit_code"] < len(cells) else ""
        if "exit_code" in columns and not re.fullmatch(r"\+?0+", exit_code):
            errors.append(f"标记 PASS 的验证行退出码必须为 0：{command}（实际 {exit_code or '空'}）")
            continue
        evidence = cells[columns["evidence"]] if "evidence" in columns and columns["evidence"] < len(cells) else ""
        if "evidence" in columns and not valid_evidence(evidence):
            errors.append(f"标记 PASS 的验证行缺少有效证据：{command}")
            continue
        file_issues = evidence_file_issues(evidence)
        if file_issues:
            errors.extend(f"{issue}（命令：{command}）" for issue in file_issues)
            continue
        cwd_text = cells[columns["cwd"]].strip().strip("`") if "cwd" in columns else "."
        if not cwd_text or cwd_text.lower() == "n/a" or "<" in cwd_text or ">" in cwd_text:
            errors.append(f"验证命令缺少有效工作目录：{command}")
            continue
        cwd = (ROOT / cwd_text).resolve() if not Path(cwd_text).is_absolute() else Path(cwd_text).resolve()
        if cwd != ROOT and ROOT not in cwd.parents:
            errors.append(f"验证工作目录越出项目：{cwd_text}")
            continue
        if not cwd.is_dir():
            errors.append(f"验证工作目录不存在：{cwd_text}")
            continue
        try:
            argv = shlex.split(command, posix=os.name != "nt")
            if os.name == "nt":
                argv = [item[1:-1] if len(item) >= 2 and item[0] == item[-1] == '"' else item for item in argv]
        except ValueError as error:
            errors.append(f"无法解析命令 {command!r}: {error}")
            continue
        controls = shell_control_tokens(command)
        if controls:
            errors.append(f"不可重放命令 {command!r}: 包含 shell 拼接/重定向 {controls[0]!r}")
            continue
        issue = replay_policy_issue(argv)
        if issue:
            errors.append(f"不可重放命令 {command!r}: {issue}")
            continue
        scope = cells[columns["scope"]].strip().strip("`*_ ") if "scope" in columns and columns["scope"] < len(cells) else ""
        name = executable(argv[0])
        if name in MAVEN_EXECUTABLES and any(value in {"-pl", "--projects"} or value.startswith(("-pl=", "--projects=")) for value in argv):
            expected = "also_make" if any(value in {"-am", "--also-make"} for value in argv) else "scoped_without_am"
            if scope != f"reactor_scope={expected}":
                errors.append(f"Maven 模块验证必须记录 reactor_scope={expected}：{command}")
                continue
        python_gate = name in {"pytest", "tox", "nox"} or (
            bool(re.fullmatch(r"python(?:\d+(?:\.\d+)?)?", name)) and len(argv) >= 3
            and argv[1] == "-m" and argv[2] in {"pytest", "unittest", "tox", "nox"}
        )
        node_gate = name in PACKAGE_MANAGERS and len(argv) >= 2 and argv[1] in {"run", "test", "exec", "dlx"}
        expanded = re.fullmatch(r"execution_scope=expanded_gate:\s*(.+)", scope)
        if (python_gate or node_gate) and scope != "execution_scope=targeted_runner" and not (
            expanded and valid_evidence(expanded.group(1))
        ):
            errors.append(f"Python/Node 验证必须记录 execution_scope=targeted_runner，或 execution_scope=expanded_gate:<原因>：{command}")
            continue
        item = (cwd, argv)
        if item in commands:
            errors.append(f"报告重复记录同一验证命令：{command}")
            continue
        commands.append(item)
        audit["passed"] += 1
    return commands, errors, audit


def python_executable(name: str) -> bool:
    return name == "py" or bool(re.fullmatch(r"python(?:\d+(?:\.\d+)?)?", name))


def direct_runner_kind(argv: list[str]) -> str | None:
    if not argv:
        return None
    name, args = executable(argv[0]), argv[1:]
    if name == "py" and args and re.fullmatch(r"-\d+(?:\.\d+)?", args[0]):
        args = args[1:]
    if python_executable(name) and len(args) >= 2 and args[0] == "-m":
        module, tail = args[1], args[2:]
        if module == "pytest":
            return "pytest"
        return "unittest" if module == "unittest" and "discover" not in tail else None
    if name == "pytest":
        return "pytest"
    if name == "npx" and args:
        name, args = executable(args[0]), args[1:]
    elif name == "pnpm" and len(args) >= 2 and args[0] in {"exec", "dlx"}:
        name, args = executable(args[1]), args[2:]
    elif name == "yarn" and len(args) >= 2 and args[0] == "dlx":
        name, args = executable(args[1]), args[2:]
    elif name == "bunx" and args:
        name, args = executable(args[0]), args[1:]
    if name not in NODE_RUNNERS:
        return None
    if name == "vitest":
        return "vitest" if "run" in args or "--run" in args else None
    if name == "jest":
        return "jest_run_tests_by_path" if "--runTestsByPath" in args or "--run-tests-by-path" in args else None
    if name == "playwright":
        return "playwright_test" if args and args[0] == "test" and "--ui" not in args else None
    return "eslint_files" if name == "eslint" and not {"--stdin", "--print-config", "--mcp"}.intersection(args) else None


def package_script(cwd: Path, argv: list[str]) -> list[str] | None:
    if not argv or executable(argv[0]) not in PACKAGE_MANAGERS or "--" not in argv:
        return None
    separator = argv.index("--")
    prefix = argv[1:separator]
    if not prefix:
        return None
    script_name = prefix[1] if prefix[0] == "run" and len(prefix) >= 2 else (
        "test" if executable(argv[0]) == "npm" and prefix[0] == "test" else ""
    )
    try:
        package_data = json.loads((cwd / "package.json").read_text(encoding="utf-8"))
        script_text = package_data.get("scripts", {}).get(script_name)
        script_argv = shlex.split(script_text) if isinstance(script_text, str) else []
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    return [*script_argv, *argv[separator + 1:]] if script_argv and not any(token in SHELL_TOKENS for token in script_argv) else None


def runner_kind(cwd: Path, argv: list[str]) -> str | None:
    return direct_runner_kind(argv) or direct_runner_kind(package_script(cwd, argv) or [])


def path_like(cwd: Path, value: str) -> bool:
    candidate = re.sub(r":\d+(?::\d+)?$", "", value.split("::", 1)[0])
    return bool(candidate) and (
        "/" in candidate or "\\" in candidate or "::" in value
        or Path(candidate).suffix.lower() in PATH_SUFFIXES or (cwd / candidate).exists()
    )


def target_argument(cwd: Path, argv: list[str], index: int, kind: str) -> bool:
    value = argv[index]
    if not value or value.startswith("-"):
        return False
    if index and argv[index - 1].startswith("-") and argv[index - 1] not in {"--", "--runTestsByPath", "--run-tests-by-path"}:
        return False
    if executable(argv[0]) in PACKAGE_MANAGERS and ("--" not in argv or index <= argv.index("--")):
        return False
    if kind == "unittest":
        return value != "discover" and bool(re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+", value) or path_like(cwd, value))
    return path_like(cwd, value)


def merge_runner_pair(cwd: Path, left: list[str], right: list[str]) -> tuple[list[str], str, int, str] | None:
    kind = runner_kind(cwd, left)
    if not kind or kind != runner_kind(cwd, right) or len(left) != len(right):
        return None
    differences = [index for index, values in enumerate(zip(left, right)) if values[0] != values[1]]
    if len(differences) != 1:
        return None
    index = differences[0]
    if not target_argument(cwd, left, index, kind) or not target_argument(cwd, right, index, kind):
        return None
    return [*left[:index + 1], right[index], *left[index + 1:]], kind, index + 2, right[index]


def maven_option(argv: list[str], option: str) -> tuple[int, int, str, str] | None:
    matches: list[tuple[int, int, str, str]] = []
    for index, value in enumerate(argv):
        if option == "test" and value.startswith("-Dtest=") and value != "-Dtest=":
            matches.append((index, index + 1, "-Dtest=", value[len("-Dtest="):]))
        elif option == "projects" and value in {"-pl", "--projects"} and index + 1 < len(argv) and argv[index + 1]:
            matches.append((index, index + 2, value, argv[index + 1]))
        elif option == "projects" and value.startswith(("-pl=", "--projects=")) and value.rsplit("=", 1)[1]:
            prefix, selected = value.split("=", 1)
            matches.append((index, index + 1, f"{prefix}=", selected))
    return matches[0] if len(matches) == 1 else None


def merge_maven_pair(left: list[str], right: list[str]) -> tuple[list[str], str] | None:
    if executable(left[0]) not in MAVEN_EXECUTABLES or executable(left[0]) != executable(right[0]):
        return None
    for option, kind in (("test", "maven_test_selectors"), ("projects", "maven_projects")):
        left_slot, right_slot = maven_option(left, option), maven_option(right, option)
        if not left_slot or not right_slot:
            continue
        if [*left[:left_slot[0]], f"<merge:{option}>", *left[left_slot[1]:]] != [
            *right[:right_slot[0]], f"<merge:{option}>", *right[right_slot[1]:]
        ]:
            continue
        values = ",".join(dict.fromkeys(
            item.strip() for value in (left_slot[3], right_slot[3]) for item in value.split(",") if item.strip()
        ))
        replacement = [left_slot[2], values] if left_slot[2] in {"-pl", "--projects"} else [f"{left_slot[2]}{values}"]
        return [*left[:left_slot[0]], *replacement, *left[left_slot[1]:]], kind
    return None


def merge_delivery_commands(commands: list[tuple[Path, list[str]]]) -> list[dict[str, object]]:
    planned: list[dict[str, object]] = []
    for cwd, argv in commands:
        item: dict[str, object] = {"cwd": cwd, "argv": argv, "merged_from": [argv]}
        if not planned or planned[-1]["cwd"] != cwd:
            planned.append(item)
            continue
        previous = planned[-1]
        merge_kind = previous.get("merge_kind")
        merged = None if merge_kind and not str(merge_kind).startswith("maven_") else merge_maven_pair(previous["argv"], argv)  # type: ignore[arg-type]
        if merged and (not merge_kind or merge_kind == merged[1]):
            previous["argv"], previous["merge_kind"] = merged
            previous["merged_from"] = [*previous["merged_from"], argv]  # type: ignore[misc]
            continue
        origins = previous["merged_from"]  # type: ignore[assignment]
        runner = None if merge_kind and str(merge_kind).startswith("maven_") else merge_runner_pair(cwd, origins[-1], argv)
        if not runner or (merge_kind and merge_kind != runner[1]):
            planned.append(item)
            continue
        if merge_kind:
            combined = list(previous["argv"])  # type: ignore[arg-type]
            insert_at = int(previous["_merge_insert_at"])
            combined.insert(insert_at, runner[3])
            previous["argv"], previous["_merge_insert_at"] = combined, insert_at + 1
        else:
            previous["argv"], previous["merge_kind"], previous["_merge_insert_at"] = runner[:3]
        previous["merged_from"] = [*previous["merged_from"], argv]  # type: ignore[misc]
    return planned


def pytest_module_fallback(cwd: Path, argv: list[str]) -> list[str] | None:
    if not argv or Path(argv[0]).name.lower() not in {"pytest", "pytest.exe"}:
        return None
    bases: list[Path] = []
    cursor = cwd
    while cursor == ROOT or ROOT in cursor.parents:
        bases.append(cursor)
        if cursor == ROOT:
            break
        cursor = cursor.parent
    interpreters = [candidate for base in bases for env in [base / "venv", *sorted(base.glob(".venv*"))] for candidate in (env / "Scripts" / "python.exe", env / "bin" / "python")]
    interpreters.append(Path(sys.executable))
    for interpreter in dict.fromkeys(path.resolve() for path in interpreters if path.is_file()):
        try:
            probe = subprocess.run([str(interpreter), "-c", "import pytest"], cwd=cwd, capture_output=True, timeout=15, check=False)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if probe.returncode == 0:
            return [str(interpreter), "-m", "pytest", *argv[1:]]
    return None


def windows_launcher_fallback(argv: list[str], *, platform: str | None = None) -> list[str] | None:
    if (platform or os.name) != "nt" or not argv:
        return None
    directory, filename = ntpath.split(argv[0])
    name, suffix = ntpath.splitext(filename)
    candidates = [argv[0], *([] if suffix else [
        ntpath.join(directory, f"{name}{extension}") if directory else f"{name}{extension}"
        for extension in (".cmd", ".bat")
    ])]
    resolved = next((found for candidate in candidates if (found := shutil.which(candidate))), None)
    if not resolved and not directory and not suffix and name.lower() in {"npm", "npx"}:
        node = shutil.which("node")
        cli = Path(node).parent / "node_modules" / "npm" / "bin" / f"{name.lower()}-cli.js" if node else None
        if node and cli and cli.is_file():
            return [node, str(cli), *argv[1:]]
    if not resolved:
        return None
    if ntpath.splitext(resolved)[1].lower() not in {".cmd", ".bat"}:
        return [resolved, *argv[1:]]
    comspec = os.environ.get("COMSPEC") or shutil.which("cmd.exe") or "cmd.exe"
    return [comspec, "/d", "/s", "/c", subprocess.list2cmdline([resolved, *argv[1:]])]


def replay_command(cwd: Path, argv: list[str], timeout: int) -> dict[str, object]:
    actual, fallback_from, fallback_kind = argv, None, None
    try:
        completed = subprocess.run(actual, cwd=cwd, capture_output=True, timeout=timeout, check=False)
    except OSError as error:
        launch_error = isinstance(error, FileNotFoundError) or getattr(error, "winerror", None) in {2, 193}
        windows = windows_launcher_fallback(argv) if launch_error else None
        pytest = pytest_module_fallback(cwd, argv) if launch_error and not windows else None
        fallback = (windows, "windows_command_launcher") if windows else ((pytest, "project_python_module") if pytest else None)
        if not fallback:
            return {"command": argv, "cwd": str(cwd.relative_to(ROOT)), "returncode": None, "error": str(error), **({"error_kind": "TOOL_MISSING"} if launch_error else {})}
        actual, fallback_kind = fallback
        fallback_from = argv
        try:
            completed = subprocess.run(actual, cwd=cwd, capture_output=True, timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as fallback_error:
            return {"command": actual, "fallback_from": argv, "cwd": str(cwd.relative_to(ROOT)), "returncode": None, "error": str(fallback_error), "error_kind": "FALLBACK_FAILED"}
    except subprocess.TimeoutExpired as error:
        return {"command": argv, "cwd": str(cwd.relative_to(ROOT)), "returncode": None, "error": str(error), "error_kind": "TIMEOUT"}
    return {
        "command": actual, "cwd": str(cwd.relative_to(ROOT)), "returncode": completed.returncode,
        "stdout": decode_output(completed.stdout)[-4000:], "stderr": decode_output(completed.stderr)[-4000:],
        **({"fallback_from": fallback_from, "fallback": fallback_kind} if fallback_from else {}),
    }


def git_value(*args: str) -> tuple[int, str]:
    try:
        completed = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=False, timeout=30)
        return completed.returncode, decode_output(completed.stdout or completed.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as error:
        return 127, str(error)


def status_entry_path(entry: str) -> str:
    return "" if len(entry) <= 3 else entry[3:].split(" -> ")[-1].strip().strip('"').replace("\\", "/")


def baseline_ignored(path: str) -> bool:
    normalized = path[2:] if path.startswith("./") else path
    return any(normalized == prefix[:-1] or normalized.startswith(prefix) for prefix in BASELINE_IGNORED_PREFIXES)


def git_snapshot(name: str) -> dict[str, Any]:
    head_rc, head = git_value("rev-parse", "HEAD")
    status_rc, status = git_value("status", "--porcelain=v1", "--untracked-files=all")
    entries = [line for line in status.splitlines() if line]
    changed_paths = sorted({status_entry_path(line) for line in entries if status_entry_path(line)})
    return {
        "version": 1, "task": task_name(name), "captured_at": now(),
        "head": head if head_rc == 0 else None, "status_returncode": status_rc,
        "status_entries": entries,
        "changed_paths": [path for path in changed_paths if not baseline_ignored(path)],
        "error": None if status_rc == 0 else status,
    }


def compare_baseline(name: str) -> dict[str, Any]:
    baseline_path = package(name) / "baseline.json"
    if not baseline_path.exists():
        return {"verdict": "FAIL", "task": task_name(name), "summary": "baseline.json 不存在"}
    baseline, current = load_json(baseline_path), git_snapshot(name)
    before = {entry for entry in baseline.get("status_entries", []) if not baseline_ignored(status_entry_path(entry))}
    after = {entry for entry in current.get("status_entries", []) if not baseline_ignored(status_entry_path(entry))}
    return {
        "verdict": "PASS" if current.get("status_returncode") == 0 else "FAIL",
        "task": task_name(name), "baseline_file": str(baseline_path.relative_to(ROOT)),
        "baseline_captured_at": baseline.get("captured_at"), "baseline_head": baseline.get("head"),
        "current_head": current.get("head"), "head_changed": baseline.get("head") != current.get("head"),
        "introduced_entries": sorted(after - before), "resolved_entries": sorted(before - after),
        "current_changed_paths": current.get("changed_paths", []),
        "summary": "已生成修改前后基线差异" if current.get("status_returncode") == 0 else current.get("error"),
    }


def execution_fingerprint(paths: list[str] | None = None, head: object = None) -> dict[str, object]:
    snapshot = git_snapshot("execution-ledger") if paths is None else None
    active_paths = paths if paths is not None else snapshot.get("changed_paths", [])
    paths = [
        path for path in active_paths
        if not any(path == prefix[:-1] or path.startswith(prefix) for prefix in EXECUTION_IGNORED_PREFIXES)
    ]
    files = []
    for path in paths:
        candidate = ROOT / path
        stat = candidate.stat() if candidate.exists() else None
        files.append({"path": path, "size": stat.st_size if stat else None, "mtime_ns": stat.st_mtime_ns if stat else None})
    state = {
        "head": head if snapshot is None else snapshot.get("head"),
        "status_returncode": 0 if snapshot is None else snapshot.get("status_returncode"), "files": files,
    }
    state["digest"] = hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()
    return state


def report_path_values(path: Path, section: str, headers: set[str]) -> list[str]:
    if not path.is_file():
        return []
    active, column, values = False, None, []
    for raw in path.read_text(encoding="utf-8").splitlines():
        heading = re.match(r"^##\s+(.+?)\s*$", raw)
        if heading:
            active, column = heading.group(1).strip() == section, None
            continue
        if not active or not raw.lstrip().startswith("|"):
            continue
        cells = [cell.strip().strip("`*_ ") for cell in raw.strip().strip("|").split("|")]
        lowered = [re.sub(r"\s+", " ", cell.lower()) for cell in cells]
        if column is None:
            column = next((index for index, value in enumerate(lowered) if value in headers), None)
            continue
        if column >= len(cells) or set("".join(cells)) <= {"-", ":", " "}:
            continue
        value = cells[column].replace("\\", "/").removeprefix("./")
        if value.lower() in INVALID_EVIDENCE or "<" in value or ">" in value or any(char in value for char in "*?[]"):
            continue
        values.append(value.rstrip("/"))
    return values


def verification_scope(task: str, role: str) -> tuple[list[str], list[str]]:
    target = package(task)
    dev, test = target / "dev-log.md", target / "test-report.md"
    values = [
        *report_path_values(dev, "Changed Files", {"file", "文件"}),
        *report_path_values(dev, "Verification Inputs", {"path", "路径"}),
    ]
    if role == "test-engineer":
        values.extend(report_path_values(test, "Verification Inputs", {"path", "路径"}))
        values.extend(report_path_values(test, "Persisted Test Assets", {"path", "路径"}))
    normalized, errors = [], []
    for value in dict.fromkeys(values):
        candidate = (ROOT / value).resolve()
        if candidate != ROOT and ROOT not in candidate.parents:
            errors.append(f"验证输入路径越出项目：{value}")
        elif any(value == prefix[:-1] or value.startswith(prefix) for prefix in EXECUTION_IGNORED_PREFIXES):
            errors.append(f"验证输入不能指向 Harness 控制面：{value}")
        else:
            normalized.append(value)
    if not normalized:
        errors.append(f"{ROLE_REPORT[role]} 必须声明至少一个任务文件或 Verification Inputs 路径")
    return sorted(normalized), errors


def explicit_verification_scope(values: list[str]) -> tuple[list[str], list[str]]:
    normalized, errors = [], []
    for raw in dict.fromkeys(values):
        value = raw.strip().replace("\\", "/").removeprefix("./").rstrip("/")
        candidate = (ROOT / value).resolve()
        if not value or value in {"."} or any(char in value for char in "*?[]"):
            errors.append(f"验证输入路径无效：{raw or '空'}")
        elif candidate != ROOT and ROOT not in candidate.parents:
            errors.append(f"验证输入路径越出项目：{value}")
        elif any(value == prefix[:-1] or value.startswith(prefix) for prefix in EXECUTION_IGNORED_PREFIXES):
            errors.append(f"验证输入不能指向 Harness 控制面：{value}")
        else:
            normalized.append(value)
    if not normalized:
        errors.append("必须声明至少一个有界验证输入路径")
    return sorted(normalized), errors


def path_in_scope(path: str, scopes: list[str]) -> bool:
    normalized = path.rstrip("/")
    return any(normalized == scope or normalized.startswith(scope + "/") for scope in scopes)


def scoped_fingerprint(scopes: list[str], snapshot: dict[str, object] | None = None) -> dict[str, object]:
    current = snapshot or git_snapshot("scoped-fingerprint")
    changed = [str(path) for path in current.get("changed_paths", []) if path_in_scope(str(path), scopes)]
    head_objects = []
    for scope in scopes:
        returncode, value = git_value("rev-parse", f"HEAD:{scope}")
        head_objects.append({"path": scope, "object": value if returncode == 0 else "MISSING"})
    worktree = []
    for path in changed:
        candidate = ROOT / path
        worktree.append({
            "path": path,
            "sha256": file_sha256(candidate) if candidate.is_file() else "MISSING",
        })
    state: dict[str, object] = {
        "version": 2, "scope_paths": scopes, "head_objects": head_objects, "worktree": worktree,
        "status_returncode": current.get("status_returncode"),
    }
    state["digest"] = hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()
    return state


def command_key(cwd: Path, argv: list[str], scope_paths: list[str]) -> str:
    relative = "." if cwd == ROOT else str(cwd.relative_to(ROOT))
    return hashlib.sha256(json.dumps({"cwd": relative, "argv": argv, "scope": scope_paths}, sort_keys=True).encode()).hexdigest()


def run_evidence_ledger(
    task: str, role: str, cwd_text: str, command: str, *, record: bool, exit_code: int | None,
    evidence: str, input_paths: list[str],
) -> dict[str, object]:
    name, target = task_name(task), package(task)
    if not target.is_dir():
        raise ValueError(f"task package not found: harness/specs/{name}")
    cwd = (ROOT / cwd_text).resolve() if not Path(cwd_text).is_absolute() else Path(cwd_text).resolve()
    if (cwd != ROOT and ROOT not in cwd.parents) or not cwd.is_dir():
        raise ValueError(f"invalid project working directory: {cwd_text}")
    try:
        argv = shlex.split(command, posix=os.name != "nt")
    except ValueError as error:
        raise ValueError(f"invalid command argv: {error}") from error
    controls, policy = shell_control_tokens(command), replay_policy_issue(argv)
    if controls or policy:
        raise ValueError(policy or f"command contains shell control token: {controls[0]}")
    declared_scope, scope_errors = verification_scope(name, role)
    if input_paths:
        scope_paths, scope_errors = explicit_verification_scope(input_paths)
    else:
        scope_paths = declared_scope
    if scope_errors:
        return {
            "task": name, "role": role, "verdict": "FAIL", "status": "SCOPE_ERROR",
            "errors": scope_errors, "summary": "先在报告 Verification Inputs 或 --input 中声明有界验证输入",
        }
    fingerprint, key = scoped_fingerprint(scope_paths), command_key(cwd, argv, scope_paths)
    baseline_path = target / "baseline.json"
    baseline_sha256 = file_sha256(baseline_path) if baseline_path.is_file() else None
    ledger_path = HARNESS / ".execution-ledger" / f"{name}--{role}.json"
    ledger = load_json(ledger_path, {"version": 1, "task": name, "role": role, "entries": {}})
    entries = ledger.get("entries", {}) if isinstance(ledger, dict) else {}
    entry = entries.get(key) if isinstance(entries, dict) else None
    relative = "." if cwd == ROOT else str(cwd.relative_to(ROOT))
    base = {
        "task": name, "role": role, "cwd": relative, "argv": argv,
        "verification_scope": scope_paths, "verification_fingerprint": fingerprint["digest"],
        "baseline_sha256": baseline_sha256,
    }
    if fingerprint["status_returncode"] != 0:
        return {**base, "verdict": "FAIL", "status": "FINGERPRINT_ERROR", "summary": "无法读取 Git 业务源码状态，禁止复用或记录"}
    if record:
        if exit_code is None or exit_code != 0 or not valid_evidence(evidence) or evidence_file_issues(evidence):
            return {**base, "verdict": "FAIL", "status": "REJECTED", "summary": "只记录退出码 0 且证据有效的已完成验证"}
        entries[key] = {**base, "exit_code": exit_code, "evidence": evidence, "recorded_at": now()}
        ledger.update(version=1, task=name, role=role, entries=entries)
        write_json(ledger_path, ledger)
        return {**base, "verdict": "PASS", "status": "RECORDED", "ledger_file": str(ledger_path.relative_to(ROOT))}
    if not isinstance(entry, dict):
        return {**base, "verdict": "FAIL", "status": "MISS", "summary": "当前角色没有相同命令的成功记录"}
    if entry.get("verification_fingerprint") != fingerprint["digest"] or entry.get("baseline_sha256") != baseline_sha256:
        return {**base, "verdict": "FAIL", "status": "STALE", "summary": "验证输入状态或任务轮次已变化，旧证据不可复用"}
    stored_evidence = str(entry.get("evidence", ""))
    if entry.get("exit_code") != 0 or not valid_evidence(stored_evidence) or evidence_file_issues(stored_evidence):
        return {**base, "verdict": "FAIL", "status": "STALE", "summary": "账本证据已经缺失或无效，禁止复用"}
    return {**base, "verdict": "PASS", "status": "REUSABLE", "evidence": stored_evidence, "recorded_at": entry.get("recorded_at")}


def report_semantic_issues(path: Path, role: str, commands: list[tuple[Path, list[str]]]) -> list[str]:
    issues: list[str] = []
    maven_groups: dict[tuple[Path, str, tuple[str, ...]], list[tuple[int, str]]] = {}
    ranks = {"compile": 1, "test": 2, "package": 3, "verify": 4, "install": 5, "deploy": 6}
    for cwd, argv in commands:
        if executable(argv[0]) not in MAVEN_EXECUTABLES:
            continue
        goals = [(ranks[value.lower()], value.lower()) for value in argv[1:] if value.lower() in ranks]
        if goals:
            project = maven_option(argv, "projects")
            profiles = tuple(sorted(
                value for index, value in enumerate(argv[1:], 1)
                if value.startswith("-P") or index > 1 and argv[index - 1] in {"-P", "--activate-profiles"}
            ))
            maven_groups.setdefault((cwd, project[3] if project else "", profiles), []).append(max(goals))
    for values in maven_groups.values():
        if len(values) > 1:
            issues.append(f"最终证据包含重叠 Maven 生命周期：{', '.join(value[1] for value in values)}；只保留最高必要入口")
    if role != "test-engineer":
        return issues
    text, active, columns = path.read_text(encoding="utf-8"), False, None
    covered: set[str] = set()
    for raw in text.splitlines():
        if raw.strip() == "### Class Coverage Summary":
            active, columns = True, None
            continue
        if active and raw.startswith("### "):
            break
        if not active or not raw.lstrip().startswith("|"):
            continue
        cells = [cell.strip().strip("`*_ ") for cell in raw.strip().strip("|").split("|")]
        lowered = [cell.lower() for cell in cells]
        if "class" in lowered and "result" in lowered:
            columns = {"class": lowered.index("class"), "result": lowered.index("result"), "evidence": next((i for i, v in enumerate(lowered) if "evidence" in v), -1), "reason": next((i for i, v in enumerate(lowered) if "理由" in v or "reason" in v), -1)}
            continue
        if not columns or not cells or cells[0] not in {"A", "B", "C", "D"}:
            continue
        category, result = cells[columns["class"]], cells[columns["result"]].upper()
        covered.add(category)
        evidence = cells[columns["evidence"]] if columns["evidence"] >= 0 else ""
        reason = cells[columns["reason"]] if columns["reason"] >= 0 else ""
        if result == "PASS" and not valid_evidence(evidence):
            issues.append(f"TE Class {category} PASS 缺少有效证据")
        elif result == "PASS":
            issues.extend(f"TE Class {category} {issue}" for issue in evidence_file_issues(evidence))
        elif result == "N/A" and not valid_evidence(reason):
            issues.append(f"TE Class {category} N/A 缺少有效理由")
        elif result not in {"PASS", "N/A"}:
            issues.append(f"TE Class {category} 未声明 PASS 或有理由的 N/A：{result or '空'}")
    if covered != {"A", "B", "C", "D"}:
        issues.append("TE Class Coverage Summary 必须包含 A/B/C/D 四类")
    active, columns, checked = False, None, set()
    required = set(load_contract().get("checklists", {}).get("test-report.md", []))
    for raw in text.splitlines():
        if raw.strip() == "## Checklist Results":
            active, columns = True, None
            continue
        if active and raw.startswith("## "):
            break
        if not active or not raw.lstrip().startswith("|"):
            continue
        cells = [cell.strip().strip("`*_ ") for cell in raw.strip().strip("|").split("|")]
        lowered = [cell.lower() for cell in cells]
        if "check id" in lowered and "result" in lowered:
            columns = {"id": lowered.index("check id"), "result": lowered.index("result"), "evidence": next((i for i, v in enumerate(lowered) if "evidence" in v), -1), "reason": next((i for i, v in enumerate(lowered) if "理由" in v or "notes" in v), -1)}
            continue
        if not columns or not cells or cells[columns["id"]] not in required:
            continue
        check_id, result = cells[columns["id"]], cells[columns["result"]].upper()
        checked.add(check_id)
        evidence = cells[columns["evidence"]] if columns["evidence"] >= 0 else ""
        reason = cells[columns["reason"]] if columns["reason"] >= 0 else ""
        if result == "PASS" and not valid_evidence(evidence):
            issues.append(f"{check_id} PASS 缺少有效证据")
        elif result == "PASS":
            issues.extend(f"{check_id} {issue}" for issue in evidence_file_issues(evidence))
        elif result == "N/A" and not valid_evidence(reason):
            issues.append(f"{check_id} N/A 缺少有效理由")
        elif result not in {"PASS", "N/A"}:
            issues.append(f"{check_id} 未声明 PASS 或有理由的 N/A：{result or '空'}")
    if checked != required:
        issues.append(f"TE Checklist Results 缺少确定性结果：{', '.join(sorted(required - checked))}")
    return issues


def run_delivery(task: str, role: str, timeout: int, total_timeout: int, replay: bool = False) -> dict[str, object]:
    name, target = task_name(task), package(task)
    report = target / ROLE_REPORT[role]
    declared = conclusion(report)
    result: dict[str, object] = {
        "task": name, "role": role, "report": str(report.relative_to(ROOT)),
        "declared_conclusion": declared, "mode": "replay" if replay else "evidence_audit",
        "checks": [], "warnings": [], "audited_at": now(),
    }
    if declared != "PASS":
        result.update(verdict="FAIL", summary=f"{report.name} 未声明 PASS")
        return result
    strict = any("harness-document:" in path.read_text(encoding="utf-8") for path in target.glob("*.md"))
    format_issues = document_format_issues(report, load_contract(), strict=strict)
    if format_issues:
        result.update(verdict="FAIL", summary="交付报告结构不符合当前模板契约", errors=format_issues)
        return result
    result["report_sha256"] = file_sha256(report)
    if role == "test-engineer":
        report_time = report.stat().st_mtime_ns
        stale = [filename for filename in ("dev-log.md", "code-review.md") if not (target / filename).is_file() or (target / filename).stat().st_mtime_ns > report_time]
        if stale:
            result.update(verdict="FAIL", summary="TE 产物早于最新 Dev/CR，禁止审计旧测试证据", errors=[f"stale input: {value}" for value in stale], error_kind="STALE_DELIVERY")
            return result
    baseline = compare_baseline(name)
    result["baseline"] = baseline
    if strict and baseline.get("verdict") != "PASS":
        result.update(verdict="FAIL", summary="缺少可比较的修改前基线", errors=[str(baseline.get("summary"))])
        return result
    baseline_path = target / "baseline.json"
    result["baseline_sha256"] = file_sha256(baseline_path) if baseline_path.is_file() else None
    scope_paths, scope_errors = verification_scope(name, role)
    current_paths = list(baseline.get("current_changed_paths", []))
    if scope_errors and strict:
        result.update(verdict="FAIL", summary="交付报告缺少可验证的任务范围", errors=scope_errors)
        return result
    if scope_errors:
        scope_paths = [
            path for path in current_paths
            if not any(path == prefix[:-1] or path.startswith(prefix) for prefix in EXECUTION_IGNORED_PREFIXES)
        ]
        result["warnings"].append("旧报告未声明 Verification Inputs；本轮兼容性审计使用全业务工作区范围")  # type: ignore[union-attr]
    snapshot = {
        "head": baseline.get("current_head"), "status_returncode": 0,
        "changed_paths": current_paths,
    }
    scoped = scoped_fingerprint(scope_paths, snapshot)
    workspace = execution_fingerprint(current_paths, baseline.get("current_head"))
    result.update(
        verification_scope=scope_paths, verification_fingerprint=scoped["digest"],
        workspace_observation={"digest": workspace["digest"], "changed_paths": current_paths},
    )
    commands, parse_errors, command_audit = markdown_commands(report, role)
    if command_audit["rows"] == 0:
        parse_errors.append("报告没有真实验证证据行；至少记录一条 PASS，或一条有明确理由的 N/A")
    parse_errors.extend(report_semantic_issues(report, role, commands))
    if parse_errors:
        result.update(verdict="FAIL", summary="交付报告中的验证证据无效", errors=parse_errors)
        return result
    if not replay:
        result["command_audit"] = {"reported": len(commands), **command_audit}
        result.update(verdict="PASS", summary=f"文档结论 PASS；审计 {command_audit['passed']} 条已执行证据和 {command_audit['na']} 条有理由 N/A，未重复运行项目命令")
        return result
    planned = merge_delivery_commands(commands)
    result["command_plan"] = {"reported": len(commands), "planned_after_merge": len(planned), "merged": len(commands) - len(planned)}
    checks: list[dict[str, object]] = []
    deadline = time.monotonic() + total_timeout
    for command in planned:
        cwd, argv = command["cwd"], command["argv"]
        remaining = int(deadline - time.monotonic())
        if remaining <= 0:
            checks.append({"command": argv, "cwd": str(cwd.relative_to(ROOT)), "returncode": None, "error_kind": "TOTAL_TIMEOUT", "error": "delivery 总耗时预算已用尽"})
            break
        check = replay_command(cwd, argv, min(timeout, remaining))
        if command.get("merge_kind"):
            check.update(merge_kind=command["merge_kind"], merged_from=command["merged_from"])
        checks.append(check)
        if check.get("returncode") != 0:
            break
    result["checks"] = checks
    failed = [check for check in checks if check.get("returncode") != 0]
    if failed:
        result.update(verdict="FAIL", summary=f"{len(failed)} 条交付验证命令失败")
    else:
        result.update(verdict="PASS", summary=f"文档结论 PASS；执行 {len(checks)} 条可复现命令")
        if not checks:
            result["warnings"].append("报告未提供可执行命令；PM 必须确认所有门槛均有明确 N/A 理由")  # type: ignore[union-attr]
    return result


def load_board() -> dict[str, list[str]]:
    if not BOARD.exists():
        return {}
    rows: dict[str, list[str]] = {}
    for line in BOARD.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) >= 6:
            try:
                rows[task_name(cells[0])] = cells[:6]
            except ValueError:
                continue
    return rows


def atomic_write_board(rows: dict[str, list[str]]) -> None:
    lines = [
        "# Harness Task Board", "", "| Task | Profile | Status | Stage | Updated | Note |",
        "| --- | --- | --- | --- | --- | --- |",
        *("| " + " | ".join(rows[key]) + " |" for key in sorted(rows)),
    ]
    BOARD.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=BOARD.parent, prefix=".board-", suffix=".tmp", delete=False
        ) as handle:
            handle.write("\n".join(lines) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.replace(temporary, BOARD)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def update_board(
    name: str, *, profile: str | None = None, status: str | None = None,
    stage: str | None = None, note: str | None = None,
) -> list[str]:
    name = task_name(name)
    if status is not None and status not in STATUSES:
        raise ValueError(f"invalid board status: {status}")
    if stage is not None and not STAGE_RE.fullmatch(stage):
        raise ValueError(f"invalid board stage: {stage}")
    rows = load_board()
    current = rows.get(name, [name, profile or "standard", status or "PROPOSE", stage or "proposal", now(), note or ""])
    if profile is not None:
        current[1] = profile
    if status is not None:
        current[2] = status
    if stage is not None:
        current[3] = stage
    current[4] = now()
    if note is not None:
        current[5] = note.replace("|", "/").replace("\n", " ")[:500]
    rows[name] = current
    atomic_write_board(rows)
    return current


def board_row(name: str) -> list[str] | None:
    return load_board().get(task_name(name))


def run_readiness(task: str, profile: str, require_apply_state: bool = False) -> dict[str, object]:
    name, target = task_name(task), package(task)
    contract = load_contract()
    required = ["proposal.md", "requirements.md", "design.md", "tasks.md"]
    gate = "design.md" if profile == "quick" else "readiness-review.md"
    if profile != "quick":
        required.append(gate)
    if profile == "refactor":
        required.append("impact-analysis.md")
    missing = [filename for filename in required if not (target / filename).exists()]
    strict = any("harness-document:" in path.read_text(encoding="utf-8") for path in target.glob("*.md"))
    format_issues = [
        issue for filename in required if (target / filename).exists()
        for issue in document_format_issues(target / filename, contract, strict=strict)
    ]
    gate_result = conclusion(target / gate)
    stale: list[str] = []
    if (target / gate).exists():
        gate_time = (target / gate).stat().st_mtime_ns
        inputs = ["proposal.md", "requirements.md", "design.md", *(["impact-analysis.md"] if profile == "refactor" else [])]
        stale = [filename for filename in inputs if (target / filename).exists() and (target / filename).stat().st_mtime_ns > gate_time]
    row = board_row(name)
    board_status = row[2] if row else None
    state_ok = not require_apply_state or board_status in {"AWAITING_APPLY", "AWAITING_ARCHIVE"}
    ok = not missing and not format_issues and gate_result == "PASS" and not stale and state_ok
    return {
        "task": name, "profile": profile, "verdict": "PASS" if ok else "FAIL",
        "missing": missing, "gate": gate, "gate_conclusion": gate_result,
        "stale_inputs": stale, "format_issues": format_issues, "board_status": board_status,
        "summary": "就绪门禁通过" if ok else "就绪产物缺失、结论未通过、上游晚于评审或任务尚未完成本轮 propose",
    }


def run_apply_close(task: str) -> dict[str, object]:
    name, target = task_name(task), package(task)
    contract, errors, routes, reports, warnings = load_contract(), [], [], {}, []
    for filename, (expected, owner) in APPLY_REPORTS.items():
        path, declared = target / filename, conclusion(target / filename)
        issues = [f"{filename} 缺失"] if not path.is_file() else document_format_issues(path, contract, strict=True)
        if declared != expected:
            issues.append(f"{filename} 必须以唯一的 ## Conclusion 声明 {expected}，实际为 {declared or '缺失'}")
        reports[filename] = {"conclusion": declared, "format_issues": issues}
        if issues:
            errors.extend(issues)
            routes.append({"owner": owner, "artifact": filename})
    delivery_results: dict[str, object] = {}
    current_snapshot = git_snapshot(name)
    current_paths = list(current_snapshot.get("changed_paths", []))
    current_workspace = execution_fingerprint(current_paths, current_snapshot.get("head"))
    if current_snapshot.get("status_returncode") != 0:
        errors.append("无法读取 Git 业务源码状态，apply-close 禁止复用旧 delivery 结果")
    for role, filename in ROLE_REPORT.items():
        result_path = HARNESS / ".hook-results" / f"{name}--{role}.json"
        path = target / filename
        payload = load_json(result_path, {})
        delivery_results[role] = payload
        owner = "Dev" if role == "developer" else "TE"
        scope_paths = payload.get("verification_scope", [])
        scope_valid = isinstance(scope_paths, list) and bool(scope_paths) and all(isinstance(value, str) for value in scope_paths)
        current_scoped = scoped_fingerprint(scope_paths, current_snapshot) if scope_valid else {}
        identity_ok = (
            payload.get("verdict") == "PASS" and payload.get("task") == name and payload.get("role") == role
            and payload.get("mode") == "evidence_audit" and path.is_file()
            and payload.get("report_sha256") == file_sha256(path)
            and scope_valid and payload.get("verification_fingerprint") == current_scoped.get("digest")
            and (target / "baseline.json").is_file()
            and payload.get("baseline_sha256") == file_sha256(target / "baseline.json")
        )
        if not identity_ok:
            errors.append(f"{role} delivery gate 缺少绑定当前 task/role/report/baseline/verification-scope 的 evidence_audit PASS 结果")
            routes.append({"owner": owner, "artifact": filename})
        elif result_path.stat().st_mtime_ns < path.stat().st_mtime_ns:
            errors.append(f"{role} delivery gate 早于最新 {filename}，必须重新验证")
            routes.append({"owner": owner, "artifact": filename})
        observation = payload.get("workspace_observation", {})
        if identity_ok and isinstance(observation, dict) and observation.get("digest") != current_workspace["digest"]:
            unrelated = [value for value in current_paths if not path_in_scope(value, scope_paths if scope_valid else [])]
            warnings.append(f"{role} delivery 后检测到验证范围外工作区变化：{', '.join(unrelated) if unrelated else 'HEAD/范围外文件状态变化'}")
    ordered = [target / filename for filename in APPLY_REPORTS]
    if all(path.is_file() for path in ordered):
        if ordered[1].stat().st_mtime_ns < ordered[0].stat().st_mtime_ns:
            errors.append("code-review.md 早于 dev-log.md，Dev 产物修订后必须重新 CR")
            routes.append({"owner": "CR", "artifact": "code-review.md"})
        if ordered[2].stat().st_mtime_ns < max(ordered[0].stat().st_mtime_ns, ordered[1].stat().st_mtime_ns):
            errors.append("test-report.md 早于 Dev/CR 最新产物，必须重新 TE")
            routes.append({"owner": "TE", "artifact": "test-report.md"})
    row = board_row(name)
    status = row[2] if row else None
    if status not in {"APPLY", "AWAITING_ARCHIVE"}:
        errors.append(f"board 状态必须是 APPLY 或 AWAITING_ARCHIVE，实际为 {status}")
    unique_routes = list({(item["owner"], item["artifact"]): item for item in routes}.values())
    return {
        "task": name, "verdict": "PASS" if not errors else "FAIL",
        "summary": "apply close gate 通过" if not errors else "交付链尚未闭合；按 owner 修复后重新走下游评审",
        "reports": reports, "delivery_results": delivery_results, "errors": errors,
        "warnings": list(dict.fromkeys(warnings)), "return_routes": unique_routes, "board_status": status,
    }


def transition_board(task: str, *, profile: str | None, status: str, stage: str, note: str | None) -> dict[str, object]:
    name = task_name(task)
    if status == "AWAITING_ARCHIVE":
        gate = run_apply_close(name)
        if gate["verdict"] != "PASS":
            return gate
    current = update_board(name, profile=profile, status=status, stage=stage, note=note)
    return {"ok": True, "task": name, "profile": current[1], "status": current[2], "stage": current[3], "verdict": "PASS"}


def run_init(task: str, description: str, profile: str) -> dict[str, object]:
    name, target = task_name(task), package(task)
    existed = target.exists()
    if not existed:
        target.mkdir(parents=True)
        shutil.copyfile(HARNESS / "templates" / "change" / "proposal.md", target / "proposal.md")
    write_json(target / "baseline.json", git_snapshot(name))
    update_board(
        name, profile=profile, status="PROPOSE", stage="proposal",
        note=("修订模式：旧的下游结论失效，重新执行 BA→SA→RR" if existed else description or "新任务"),
    )
    return {
        "ok": True, "task": name, "profile": profile, "mode": "revise" if existed else "new",
        "created": (["baseline.json"] if existed else ["proposal.md", "baseline.json"]),
        "next": "DISPATCH_SA_IMPACT" if profile == "refactor" else "DISPATCH_BA",
    }


def run_stage(task: str, stage: str, profile: str | None) -> dict[str, object]:
    name, target, contract = task_name(task), package(task), load_contract()
    if not target.is_dir():
        raise ValueError(f"task package not found: harness/specs/{name}")
    if stage not in contract["stages"]:
        raise ValueError(f"unknown stage: {stage}")
    if profile == "quick" and stage == "readiness":
        return {"ok": True, "task": name, "stage": stage, "skipped": "quick profile uses SA self-check"}
    if profile and stage not in contract["profiles"][profile]:
        raise ValueError(f"stage {stage!r} is not part of profile {profile!r}")
    created, preserved = [], []
    for filename in contract["stages"][stage]["documents"]:
        destination = target / filename
        if destination.exists():
            preserved.append(filename)
        else:
            shutil.copyfile(HARNESS / "templates" / "change" / filename, destination)
            created.append(filename)
    update_board(name, profile=profile, status="IN_PROGRESS", stage=stage, note=f"文档就位：{', '.join(created) or '保留现有内容'}")
    return {"ok": True, "task": name, "stage": stage, "created": created, "preserved": preserved}


def chinese_summary(task_dir: Path, name: str) -> str:
    proposal = task_dir / "proposal.md"
    if proposal.exists():
        for line in proposal.read_text(encoding="utf-8").splitlines():
            value = line.lstrip("# ").strip()
            if value and "<" not in value and re.search(r"[\u4e00-\u9fff]", value):
                return value
    return f"归档变更任务：{name}"


def update_archive_index(name: str, summary: str) -> None:
    index = ARCHIVE / "index.md"
    lines = index.read_text(encoding="utf-8").splitlines() if index.exists() else [
        "# Harness Archive Index", "", "| Change ID | Status | Archived At | 中文任务描述 | Package |", "| --- | --- | --- | --- | --- |"
    ]
    if not any(re.search(rf"\|\s*{re.escape(name)}\s*\|", line) for line in lines):
        lines.append(f"| {name} | DONE | {date.today().isoformat()} | {summary.replace('|', '/')} | `harness/archive/{name}/` |")
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text("\n".join(lines) + "\n", encoding="utf-8")


def memory_entry_issues(name: str) -> list[str]:
    entries = ROOT / "harness" / "memory" / "entries"
    if not entries.is_dir():
        return []
    issues: list[str] = []
    required_fields = ("trigger", "reuse_scope", "evidence", "dedupe_key")
    required_sections = ("症状（怎么爆的）", "根因（为什么会发生）", "修复（怎么修）", "防复发措施（怎么防复发）", "复发检测（机器怎么抓）")
    for path in entries.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        if not re.search(rf"(?m)^source_change:\s*{re.escape(name)}\s*$", text):
            continue
        values = {field: (match.group(1).strip() if (match := re.search(rf"(?m)^{field}:\s*(.+)$", text)) else "") for field in required_fields}
        if values["trigger"] not in {"BLOCK", "REJECT", "FAIL", "PITFALL"}:
            issues.append(f"{path.name}: trigger 必须来自真实 BLOCK/REJECT/FAIL/PITFALL")
        for field in ("reuse_scope", "evidence", "dedupe_key"):
            if not values[field] or "<" in values[field]:
                issues.append(f"{path.name}: {field} 缺少可核对值")
        for section in required_sections:
            if not re.search(rf"(?m)^##\s+{re.escape(section)}\s*$", text):
                issues.append(f"{path.name}: 缺少章节 {section}")
    return issues


def markdown_section(path: Path, heading: str) -> str:
    if not path.is_file():
        return ""
    matched = re.search(
        rf"(?ims)^##\s+{re.escape(heading)}\s*\n(.*?)(?=^##\s+|\Z)", path.read_text(encoding="utf-8"),
    )
    return matched.group(1).strip() if matched else ""


def memory_drafts(name: str) -> dict[str, str]:
    target, drafts = package(name), {}
    for filename in ("readiness-review.md", "dev-log.md", "code-review.md", "test-report.md"):
        path = target / filename
        value = markdown_section(path, "Reusable Experience Draft")
        template = markdown_section(HARNESS / "templates" / "change" / filename, "Reusable Experience Draft")
        normalized = value.strip().strip("`*_ ").lower()
        if value and value != template and normalized not in INVALID_EVIDENCE | {"无", "没有", "无。"}:
            drafts[str(path.relative_to(ROOT)) + "#Reusable Experience Draft"] = hashlib.sha256(value.encode()).hexdigest()
    candidates = [*(target / "memory").glob("*.md"), *(target / "memory-drafts").glob("*.md")]
    memory_root = ROOT / "harness" / "memory"
    for path in memory_root.glob("*.md") if memory_root.is_dir() else []:
        if path.name in {"README.md", "index.md"}:
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(rf"(?m)^source_change:\s*{re.escape(name)}\s*$", text) or name in path.stem:
            candidates.append(path)
    for path in candidates:
        if path.is_file() and path.stat().st_size:
            drafts[str(path.relative_to(ROOT))] = file_sha256(path)
    return dict(sorted(drafts.items()))


def memory_index_has(path: str) -> bool:
    index = ROOT / "harness" / "memory" / "index.md"
    return index.is_file() and path.replace("\\", "/") in index.read_text(encoding="utf-8").replace("\\", "/")


def memory_target(value: str) -> tuple[Path | None, str | None]:
    normalized = value.replace("\\", "/").removeprefix("./")
    path = (ROOT / normalized).resolve()
    entries = (ROOT / "harness" / "memory" / "entries").resolve()
    if path.parent != entries or path.suffix.lower() != ".md":
        return None, "记忆目标必须是 harness/memory/entries/*.md"
    return path, None


def validate_memory_disposition(
    name: str, status: str, reason: str, entry: str, dedupe_target: str,
    drafts: dict[str, str], *, recorded_hashes: object = None,
) -> list[str]:
    errors: list[str] = []
    if recorded_hashes is not None and recorded_hashes != drafts:
        errors.append("memory drafts 在 disposition 后发生变化，必须重新处置")
    if status == "none":
        if drafts:
            errors.append("存在非空 memory draft，status=none 无效")
        return errors
    if not drafts:
        errors.append(f"status={status} 但没有发现非空 memory draft")
    if status == "rejected":
        if not valid_evidence(reason):
            errors.append("rejected 必须记录明确原因")
        return errors
    selected = entry if status == "accepted" else dedupe_target
    target, path_error = memory_target(selected)
    if path_error:
        errors.append(path_error)
        return errors
    if not target or not target.is_file():
        errors.append(f"记忆目标不存在：{selected or '空'}")
        return errors
    relative = str(target.relative_to(ROOT))
    if not memory_index_has(relative):
        errors.append(f"memory index 未引用：{relative}")
    if status == "accepted":
        text = target.read_text(encoding="utf-8")
        if not re.search(rf"(?m)^source_change:\s*{re.escape(name)}\s*$", text):
            errors.append(f"accepted entry 的 source_change 不是当前任务：{relative}")
        errors.extend(memory_entry_issues(name))
    elif status == "duplicate" and not valid_evidence(reason):
        errors.append("duplicate 必须说明与既有记忆重复的原因")
    return errors


def run_memory_disposition(
    task: str, status: str, reason: str, entry: str, dedupe_target: str,
) -> dict[str, object]:
    name, target = task_name(task), package(task)
    if not target.is_dir():
        raise ValueError(f"task package not found: harness/specs/{name}")
    drafts = memory_drafts(name)
    errors = validate_memory_disposition(name, status, reason, entry, dedupe_target, drafts)
    result: dict[str, object] = {
        "version": 1, "task": name, "status": status, "draft_hashes": drafts,
        "reason": reason, "entry": entry, "dedupe_target": dedupe_target, "decided_at": now(),
        "verdict": "PASS" if not errors else "FAIL", "errors": errors,
    }
    if not errors:
        write_json(target / "memory-disposition.json", result)
        result["disposition_file"] = f"harness/specs/{name}/memory-disposition.json"
    return result


def memory_disposition_issues(name: str) -> tuple[list[str], dict[str, object]]:
    target, drafts = package(name), memory_drafts(name)
    path = target / "memory-disposition.json"
    payload = load_json(path, {})
    if not drafts and not path.is_file():
        return [], {"status": "none", "draft_hashes": {}, "implicit": True}
    if drafts and not path.is_file():
        return ["memory disposition required: 存在非空草稿但尚未 accepted/rejected/duplicate"], {}
    if not isinstance(payload, dict) or payload.get("task") != name:
        return ["memory-disposition.json 缺失当前 task 身份"], payload if isinstance(payload, dict) else {}
    status = str(payload.get("status", ""))
    if status not in {"none", "rejected", "duplicate", "accepted"}:
        return [f"memory disposition status 无效：{status or '空'}"], payload
    errors = validate_memory_disposition(
        name, status, str(payload.get("reason", "")), str(payload.get("entry", "")),
        str(payload.get("dedupe_target", "")), drafts, recorded_hashes=payload.get("draft_hashes"),
    )
    return errors, payload


def archive_index_updated(name: str) -> bool:
    index = ARCHIVE / "index.md"
    if not index.is_file():
        return False
    for line in index.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) >= 5 and cells[0] == name:
            return cells[1] == "DONE" and bool(re.search(r"[\u4e00-\u9fff]", cells[3])) and f"harness/archive/{name}/" in cells[4]
    return False


def archive_result(
    name: str, source: Path, target: Path, summary: str, *, already_archived: bool,
    memory_disposition: dict[str, object] | None = None,
) -> dict[str, object]:
    update_archive_index(name, summary)
    update_board(name, status="DONE", stage="archive", note="已归档；记忆草稿缺失不阻断归档")
    row = board_row(name)
    checks = {
        "source_absent": not source.exists(), "archive_present": target.is_dir(),
        "index_updated": archive_index_updated(name),
        "board_done": bool(row and row[2] == "DONE" and row[3] == "archive"),
    }
    ok = all(checks.values())
    return {
        "ok": ok, "task": name, "already_archived": already_archived,
        "archive": str(target.relative_to(ROOT)), "summary": summary, "postconditions": checks,
        "memory_disposition": memory_disposition or {"status": "none", "implicit": True},
        "warning": "没有非空记忆草稿，未创建长期 entry"
        if not memory_disposition or memory_disposition.get("implicit") else None,
        **({} if ok else {"error": "archive postconditions failed"}),
    }


def run_archive(task: str) -> dict[str, object]:
    name = task_name(task)
    source, target = package(name), package(name, archived=True)
    if target.is_dir() and not source.exists():
        disposition = load_json(target / "memory-disposition.json", None)
        return archive_result(name, source, target, chinese_summary(target, name), already_archived=True, memory_disposition=disposition)
    if not source.is_dir():
        raise ValueError(f"task package not found: harness/specs/{name}")
    row = board_row(name)
    if not row or row[2] != "AWAITING_ARCHIVE":
        raise ValueError("task board status must be AWAITING_ARCHIVE")
    close = run_apply_close(name)
    if close["verdict"] != "PASS":
        raise ValueError(f"apply close gate failed: {json.dumps(close, ensure_ascii=False)}")
    disposition_issues, disposition = memory_disposition_issues(name)
    if disposition_issues:
        raise ValueError(f"memory disposition failed: {disposition_issues}")
    memory_issues = memory_entry_issues(name)
    if memory_issues:
        raise ValueError(f"memory admission failed: {memory_issues}")
    if target.exists():
        raise ValueError(f"archive target already exists: harness/archive/{name}")
    summary = chinese_summary(source, name)
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(target))
    return archive_result(name, source, target, summary, already_archived=False, memory_disposition=disposition)


def run_framework() -> dict[str, object]:
    errors: list[str] = []
    try:
        contract = load_contract()
    except (OSError, json.JSONDecodeError) as error:
        return {"verdict": "FAIL", "errors": [f"contract.json: {error}"], "warnings": []}
    stages = contract.get("stages", {})
    for stage in stages.values() if isinstance(stages, dict) else []:
        for filename in stage.get("documents", []):
            if not (HARNESS / "templates" / "change" / filename).is_file():
                errors.append(f"缺少模板：{filename}")
    documents = contract.get("documents", {})
    for filename in documents if isinstance(documents, dict) else []:
        template = HARNESS / "templates" / "change" / filename
        if template.is_file():
            errors.extend(f"模板契约：{issue}" for issue in document_format_issues(template, contract, strict=True))
    for folder in ("commands", "rules", "subagents", "skills"):
        for path in (HARNESS / folder).rglob("*.md"):
            count = len(path.read_text(encoding="utf-8").splitlines())
            if count > 300:
                errors.append(f"提示文件超过 300 行：{path.relative_to(ROOT)} ({count})")
    required_skill_sections = {
        "build-test": ("## Inputs", "## Procedure", "## Decision Rules", "## Output Contract"),
        "post-verify": ("## Inputs", "## Procedure", "## Failure Branches", "## Completion Criteria"),
        "systematic-debug": ("## Inputs", "## Procedure", "## Branches", "## Output Contract"),
        "code-review": ("## Inputs", "## Procedure", "## Decision Rules", "## Output Contract"),
        "test-e2e": ("## Inputs", "## Procedure", "## Coverage And Routing", "## Decision Rules", "## Output Contract"),
    }
    for skill, sections in required_skill_sections.items():
        path = HARNESS / "skills" / skill / "SKILL.md"
        if not path.is_file():
            errors.append(f"缺少工程 Skill：{skill}")
            continue
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n") or f"name: {skill}" not in text or "description:" not in text:
            errors.append(f"Skill 元数据无效：{skill}")
        errors.extend(f"Skill SOP 缺少章节：{skill} -> {section}" for section in sections if section not in text)
    python_contract_paths = [
        HARNESS / "runtime.md", HARNESS / "skills" / "harness-init" / "SKILL.md",
        HARNESS / "skills" / "build-test" / "SKILL.md", HARNESS / "skills" / "post-verify" / "SKILL.md",
        HARNESS / "skills" / "build-test" / "references" / "command-discovery.md",
    ]
    for path in python_contract_paths:
        text = path.read_text(encoding="utf-8")
        missing = [marker for marker in ("Windows", "macOS", "Linux", "py -3", "python3") if marker not in text]
        if missing:
            errors.append(f"Python 三端入口契约缺失：{path.relative_to(ROOT)} -> {', '.join(missing)}")
    java_contract_paths = [
        HARNESS / "runtime.md", HARNESS / "skills" / "build-test" / "SKILL.md",
        HARNESS / "skills" / "build-test" / "references" / "command-discovery.md",
        HARNESS / "subagents" / "developer.md", HARNESS / "subagents" / "test-engineer.md",
        HARNESS / "templates" / "change" / "dev-log.md", HARNESS / "templates" / "change" / "test-report.md",
    ]
    for path in java_contract_paths:
        text = path.read_text(encoding="utf-8")
        if "最低必要生命周期" not in text or "./mvnw test" not in text or "./gradlew test" not in text:
            errors.append(f"Java 验证契约未固定最低必要生命周期：{path.relative_to(ROOT)}")
        if "`./mvnw verify`" in text or "`./gradlew build`" in text:
            errors.append(f"Java 验证契约仍把打包阶段写成默认入口：{path.relative_to(ROOT)}")
    te_contract_paths = [
        HARNESS / "subagents" / "test-engineer.md", HARNESS / "skills" / "test-e2e" / "SKILL.md",
        HARNESS / "templates" / "change" / "test-report.md", HARNESS / "checklists" / "test-engineering.md",
    ]
    for path in te_contract_paths:
        text = path.read_text(encoding="utf-8")
        missing = [marker for marker in ("覆盖分类", "1–2", "不要求截图") if marker not in text]
        if missing:
            errors.append(f"TE 有界独立验收契约缺失：{path.relative_to(ROOT)} -> {', '.join(missing)}")
    if "不继承其判断" not in (HARNESS / "subagents" / "test-engineer.md").read_text(encoding="utf-8"):
        errors.append("TE 契约缺少相对 CR 的独立判断边界")
    scope_contract_paths = [
        HARNESS / "runtime.md", HARNESS / "skills" / "build-test" / "SKILL.md",
        HARNESS / "subagents" / "developer.md", HARNESS / "subagents" / "test-engineer.md",
        HARNESS / "templates" / "change" / "dev-log.md", HARNESS / "templates" / "change" / "test-report.md",
    ]
    for path in scope_contract_paths:
        text = path.read_text(encoding="utf-8")
        if "scoped_without_am" not in text or "also_make" not in text:
            errors.append(f"Maven reactor scope 契约缺失：{path.relative_to(ROOT)}")
        if "targeted_runner" not in text or "expanded_gate" not in text or "tox/nox" not in text:
            errors.append(f"Vue/Node/Python 有界 runner 契约缺失：{path.relative_to(ROOT)}")
    runtime_lines = len((HARNESS / "runtime.md").read_text(encoding="utf-8").splitlines())
    for command in (HARNESS / "commands").glob("*.md"):
        combined = runtime_lines + len(command.read_text(encoding="utf-8").splitlines())
        if combined > 200:
            errors.append(f"启动组合超过 200 行：runtime.md + {command.name} ({combined})")
    forbidden = ("worker_lifecycle.py", "advance_change.py", "guard_harness_writes.py", "attest_worker_launch.py")
    paths = [HARNESS / "runtime.md", *(HARNESS / "commands").glob("*.md"), *(HARNESS / "rules").glob("*.md")]
    for path in paths:
        text = path.read_text(encoding="utf-8").lower()
        errors.extend(f"遗留旧状态机术语：{path.relative_to(ROOT)} -> {marker}" for marker in forbidden if marker in text)
    return {"verdict": "PASS" if not errors else "FAIL", "errors": errors, "warnings": []}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Run deterministic Harness lifecycle actions.")
    sub = result.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("task")
    init.add_argument("description", nargs="?", default="")
    init.add_argument("--profile", choices=("quick", "standard", "refactor"), default="standard")
    stage = sub.add_parser("stage")
    stage.add_argument("task")
    stage.add_argument("stage")
    stage.add_argument("--profile", choices=("quick", "standard", "refactor"))
    ready = sub.add_parser("readiness")
    ready.add_argument("task")
    ready.add_argument("--profile", choices=("quick", "standard", "refactor"), default="standard")
    ready.add_argument("--for-apply", action="store_true")
    delivery = sub.add_parser("delivery")
    delivery.add_argument("task")
    delivery.add_argument("--role", choices=tuple(ROLE_REPORT), required=True)
    delivery.add_argument("--timeout", type=int, default=300)
    delivery.add_argument("--total-timeout", type=int, default=600)
    delivery.add_argument("--replay", action="store_true", help="仅供人工诊断：实际重放报告中的项目命令")
    delivery.add_argument("--write-result", action="store_true")
    ledger = sub.add_parser("evidence-ledger")
    ledger.add_argument("task")
    ledger.add_argument("--role", choices=tuple(ROLE_REPORT), required=True)
    ledger.add_argument("--cwd", required=True)
    ledger.add_argument("--command", dest="command_text", required=True)
    ledger.add_argument("--record", action="store_true")
    ledger.add_argument("--exit-code", type=int)
    ledger.add_argument("--evidence", default="")
    ledger.add_argument("--input", action="append", default=[], help="任务相关文件或目录；可重复")
    preflight = sub.add_parser("preflight")
    preflight.add_argument("task")
    preflight.add_argument("--role", choices=tuple(ROLE_STAGE), required=True)
    preflight.add_argument("--stage", choices=("impact-analysis", *tuple(ROLE_STAGE.values())))
    disposition = sub.add_parser("memory-disposition")
    disposition.add_argument("task")
    disposition.add_argument("--status", choices=("none", "rejected", "duplicate", "accepted"), required=True)
    disposition.add_argument("--reason", default="")
    disposition.add_argument("--entry", default="")
    disposition.add_argument("--dedupe-target", default="")
    sub.add_parser("apply-close").add_argument("task")
    baseline = sub.add_parser("baseline")
    baseline.add_argument("task")
    baseline.add_argument("action", choices=("snapshot", "compare"), default="compare", nargs="?")
    board = sub.add_parser("board")
    board.add_argument("task")
    board.add_argument("--profile", choices=("quick", "standard", "refactor"))
    board.add_argument("--status", required=True)
    board.add_argument("--stage", required=True)
    board.add_argument("--note")
    sub.add_parser("archive").add_argument("task")
    sub.add_parser("framework")
    return result


def main() -> int:
    cli, result = parser(), None
    arguments = cli.parse_args()
    try:
        if arguments.command == "init":
            result = run_init(arguments.task, arguments.description, arguments.profile)
        elif arguments.command == "stage":
            result = run_stage(arguments.task, arguments.stage, arguments.profile)
        elif arguments.command == "readiness":
            result = run_readiness(arguments.task, arguments.profile, arguments.for_apply)
        elif arguments.command == "delivery":
            result = run_delivery(arguments.task, arguments.role, arguments.timeout, arguments.total_timeout, arguments.replay)
            if arguments.write_result:
                output = HARNESS / ".hook-results" / f"{task_name(arguments.task)}--{arguments.role}.json"
                write_json(output, result)
                result["result_file"] = str(output.relative_to(ROOT))
        elif arguments.command == "evidence-ledger":
            result = run_evidence_ledger(
                arguments.task, arguments.role, arguments.cwd, arguments.command_text,
                record=arguments.record, exit_code=arguments.exit_code, evidence=arguments.evidence,
                input_paths=arguments.input,
            )
        elif arguments.command == "preflight":
            result = run_worker_preflight(arguments.task, arguments.role, arguments.stage)
        elif arguments.command == "memory-disposition":
            result = run_memory_disposition(
                arguments.task, arguments.status, arguments.reason, arguments.entry, arguments.dedupe_target,
            )
        elif arguments.command == "apply-close":
            result = run_apply_close(arguments.task)
        elif arguments.command == "baseline":
            if arguments.action == "snapshot":
                name, target = task_name(arguments.task), package(arguments.task)
                if not target.is_dir():
                    raise ValueError(f"task package not found: harness/specs/{name}")
                write_json(target / "baseline.json", git_snapshot(name))
                result = {"verdict": "PASS", "task": name, "baseline_file": f"harness/specs/{name}/baseline.json"}
            else:
                result = compare_baseline(arguments.task)
        elif arguments.command == "board":
            result = transition_board(
                arguments.task, profile=arguments.profile, status=arguments.status,
                stage=arguments.stage, note=arguments.note,
            )
        elif arguments.command == "archive":
            result = run_archive(arguments.task)
        else:
            result = run_framework()
    except ValueError as error:
        cli.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if arguments.command in {"init", "stage"}:
        return 0
    if arguments.command == "archive":
        return 0 if result["ok"] else 1
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
