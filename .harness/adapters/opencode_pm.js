// OpenCode PM schema-bound tools and Task-role guard.
// Task completion observation remains fail-open; PM ownership and Task-role guards are deterministic.
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

export function createHarnessHooksPlugin(tool, root) {
const scripts = path.join(root, ".harness", "scripts");
const dispatcher = path.join(scripts, "dispatch_subagent.py");
const taskNamePattern = /^[a-z0-9]+(?:[-_][a-z0-9]+)*$/;
const allowedRoles = new Set([
  "business-analyst",
  "solution-architect",
  "readiness-reviewer",
  "developer",
  "code-reviewer",
  "test-engineer",
]);
const sessionAgents = new Map();
const activeDeliveries = new Map();
const activeTasks = new Map();

function pythonCandidates() {
  return process.platform === "win32"
    ? [["py", "-3"], ["python"], ["python3"]]
    : [["python3"], ["python"], ["py", "-3"]];
}

function toolName(input) {
  return String(input?.tool?.name || input?.tool || input?.name || input?.toolName || "").toLowerCase();
}

function requirePm(context) {
  if (context?.agent !== "harness-pm") {
    throw new Error("Harness PM tools are only available to the harness-pm Primary Agent.");
  }
}

function requireTaskName(value) {
  const name = String(value || "");
  if (!taskNamePattern.test(name)) throw new Error(`Invalid Harness change-id: ${name}`);
  return name;
}

function completedResult(title, program, args, result) {
  const payload = {
    ok: !result.error && result.status === 0,
    program,
    args,
    exit_code: typeof result.status === "number" ? result.status : null,
    stdout: String(result.stdout || "").trim(),
    stderr: String(result.stderr || result.error?.message || "").trim(),
    timed_out: Boolean(result.timedOut),
    aborted: Boolean(result.aborted),
  };
  return { title, output: JSON.stringify(payload, null, 2), metadata: payload };
}

function runChild(program, args, { timeout = 120000, input = "", signal } = {}) {
  return new Promise((resolve) => {
    let child;
    try {
      child = spawn(program, args, {
        cwd: root,
        detached: process.platform !== "win32",
        shell: false,
        windowsHide: true,
        stdio: ["pipe", "pipe", "pipe"],
      });
    } catch (error) {
      resolve({ status: null, stdout: "", stderr: "", error });
      return;
    }

    const outputLimit = 10 * 1024 * 1024;
    let stdout = "";
    let stderr = "";
    let outputBytes = 0;
    let settled = false;
    let timedOut = false;
    let aborted = false;
    let processError;

    const stop = () => {
      if (!child.pid || child.killed) return;
      if (process.platform === "win32") {
        spawn("taskkill", ["/pid", String(child.pid), "/t", "/f"], { windowsHide: true }).unref();
      } else {
        try {
          process.kill(-child.pid, "SIGTERM");
          setTimeout(() => { try { process.kill(-child.pid, "SIGKILL"); } catch {} }, 1500).unref();
        } catch { child.kill(); }
      }
    };
    const append = (target, chunk) => {
      const text = chunk.toString("utf8");
      outputBytes += Buffer.byteLength(text, "utf8");
      if (outputBytes > outputLimit) {
        processError = new Error("Harness tool output exceeded 10 MB.");
        stop();
        return target;
      }
      return target + text;
    };
    child.stdout.on("data", (chunk) => {
      stdout = append(stdout, chunk);
    });
    child.stderr.on("data", (chunk) => {
      stderr = append(stderr, chunk);
    });
    child.on("error", (error) => {
      processError = error;
    });

    const timer = setTimeout(() => {
      timedOut = true;
      stop();
    }, timeout);
    const onAbort = () => {
      aborted = true;
      stop();
    };
    if (signal) {
      if (signal.aborted) onAbort();
      else signal.addEventListener("abort", onAbort, { once: true });
    }

    child.on("close", (status) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      signal?.removeEventListener("abort", onAbort);
      resolve({ status, stdout, stderr, error: processError, timedOut, aborted });
    });

    if (input) child.stdin.end(input);
    else child.stdin.end();
  });
}

async function runProgram(title, program, args, timeout = 120000, signal) {
  const result = await runChild(program, args, { timeout, signal });
  return completedResult(title, program, args, result);
}

async function runPython(title, scriptName, args, timeout = 120000, signal) {
  const script = path.join(scripts, scriptName);
  for (const candidate of pythonCandidates()) {
    const program = candidate[0];
    const argv = [...candidate.slice(1), script, ...args];
    const result = await runChild(program, argv, { timeout, signal });
    if (result.error?.code === "ENOENT") continue;
    return completedResult(title, program, argv, result);
  }
  return {
    title,
    output: JSON.stringify({ ok: false, error: "No Python interpreter found." }, null, 2),
    metadata: { ok: false },
  };
}

async function dispatchObservation(payload, event = "stop") {
  for (const candidate of pythonCandidates()) {
    const result = await runChild(
      candidate[0],
      [...candidate.slice(1), dispatcher, "--platform", "opencode", "--audit-only", "--event", event],
      {
        input: JSON.stringify(payload || {}),
        timeout: 120000,
      },
    );
    if (result.error?.code === "ENOENT") continue;
    return;
  }
}

function taskObservationKey(input) {
  return String(input?.callID || input?.toolCallID || input?.id || input?.sessionID || "task");
}

function safeGitPath(value) {
  const raw = String(value || "").replaceAll("\\", "/");
  if (!raw || raw.startsWith("-") || path.isAbsolute(raw)) throw new Error(`Invalid Git path: ${raw}`);
  const resolved = path.resolve(root, raw);
  if (resolved !== root && !resolved.startsWith(`${root}${path.sep}`)) throw new Error(`Git path escapes project: ${raw}`);
  return path.relative(root, resolved).replaceAll("\\", "/");
}

function safePmWritePath(value) {
  const raw = String(value || "").replaceAll("\\", "/");
  if (!raw || raw.startsWith("-") || path.isAbsolute(raw)) throw new Error(`Invalid PM write path: ${raw}`);
  const normalized = path.posix.normalize(raw);
  const allowed =
    normalized === "harness/specs/README.md" ||
    normalized.startsWith("docs/") ||
    normalized.startsWith("harness/memory/");
  if (!allowed || normalized.includes("../")) throw new Error(`PM does not own this path: ${raw}`);
  const target = path.resolve(root, normalized);
  let cursor = root;
  for (const part of normalized.split("/")) {
    cursor = path.join(cursor, part);
    if (fs.existsSync(cursor) && fs.lstatSync(cursor).isSymbolicLink()) {
      throw new Error(`PM write path contains a symbolic link: ${raw}`);
    }
  }
  return target;
}

function requestedTaskRole(args) {
  for (const key of ["subagent_type", "subagentType", "agent", "agent_name", "agentName"]) {
    if (typeof args?.[key] === "string" && args[key]) return args[key];
  }
  return "";
}

const harnessChange = tool({
  description:
    "Run one schema-bound Harness PM lifecycle action. Normal delivery audits evidence; archive requires explicit disposition for nonempty memory drafts.",
  args: {
    action: tool.schema.enum(["init", "stage", "readiness", "delivery", "memory-disposition", "board", "archive"]),
    task: tool.schema.string().describe("ASCII Harness change-id only"),
    description: tool.schema.string().max(500).optional(),
    profile: tool.schema.enum(["quick", "standard", "refactor"]).optional(),
    stage: tool.schema
      .enum(["impact-analysis", "requirements", "design", "readiness", "development", "review", "testing"])
      .optional(),
    role: tool.schema.enum(["developer", "test-engineer"]).optional(),
    forApply: tool.schema.boolean().optional(),
    status: tool.schema.enum(["PROPOSE", "IN_PROGRESS", "AWAITING_APPLY", "APPLY", "AWAITING_ARCHIVE"]).optional(),
    boardStage: tool.schema.string().max(40).optional(),
    note: tool.schema.string().max(500).optional(),
    memoryStatus: tool.schema.enum(["none", "rejected", "duplicate", "accepted"]).optional(),
    reason: tool.schema.string().max(1000).optional(),
    entry: tool.schema.string().max(500).optional(),
    dedupeTarget: tool.schema.string().max(500).optional(),
  },
  async execute(args, context) {
    requirePm(context);
    const task = requireTaskName(args.task);
    const profile = args.profile || "standard";
    if (args.action === "init") {
      return runPython("Harness task initialized", "harness.py", [
        "init", task,
        args.description || "",
        "--profile",
        profile,
      ], 120000, context.abort);
    }
    if (args.action === "stage") {
      if (!args.stage) throw new Error("stage is required for action=stage");
      return runPython("Harness stage prepared", "harness.py", [
        "stage", task,
        args.stage,
        "--profile",
        profile,
      ], 120000, context.abort);
    }
    if (args.action === "readiness") {
      const argv = ["readiness", task, "--profile", profile];
      if (args.forApply) argv.push("--for-apply");
      return runPython("Harness readiness verified", "harness.py", argv, 120000, context.abort);
    }
    if (args.action === "delivery") {
      if (!args.role) throw new Error("role is required for action=delivery");
      if (activeDeliveries.has(task)) {
        const activeRole = activeDeliveries.get(task);
        const payload = { ok: false, error_kind: "DELIVERY_ALREADY_RUNNING", task, requested_role: args.role, active_role: activeRole };
        return { title: "Harness delivery rejected", output: JSON.stringify(payload, null, 2), metadata: payload };
      }
      activeDeliveries.set(task, args.role);
      try {
        return await runPython("Harness delivery evidence audited", "harness.py", ["delivery", task, "--role", args.role, "--write-result"], 660000, context.abort);
      } finally {
        activeDeliveries.delete(task);
      }
    }
    if (args.action === "memory-disposition") {
      if (!args.memoryStatus) throw new Error("memoryStatus is required for action=memory-disposition");
      const argv = ["memory-disposition", task, "--status", args.memoryStatus];
      if (args.reason) argv.push("--reason", args.reason);
      if (args.entry) argv.push("--entry", args.entry);
      if (args.dedupeTarget) argv.push("--dedupe-target", args.dedupeTarget);
      return runPython("Harness memory disposition recorded", "harness.py", argv, 120000, context.abort);
    }
    if (args.action === "board") {
      if (!args.status || !args.boardStage) {
        throw new Error("status and boardStage are required for action=board");
      }
      const argv = ["board", task, "--status", args.status, "--stage", args.boardStage];
      if (args.profile) argv.push("--profile", args.profile);
      if (args.note) argv.push("--note", args.note);
      const result = await runPython("Harness board updated", "harness.py", argv, 120000, context.abort);
      if (!result.metadata?.ok) return result;
      const payload = JSON.parse(result.metadata.stdout);
      const output = { ok: true, task: payload.task, profile: payload.profile, status: payload.status, stage: payload.stage };
      return {
        title: "Harness board updated",
        output: JSON.stringify(output, null, 2),
        metadata: { ok: true, task: payload.task, status: payload.status, stage: payload.stage },
      };
    }
    return runPython("Harness task archived", "harness.py", ["archive", task], 120000, context.abort);
  },
});

const harnessGitRead = tool({
  description:
    "Read project Git evidence without a shell. Supports status, diff, log, and HEAD only; no mutation or arbitrary Git arguments.",
  args: {
    action: tool.schema.enum(["status", "diff", "log", "head"]),
    staged: tool.schema.boolean().optional(),
    paths: tool.schema.array(tool.schema.string()).max(50).optional(),
    limit: tool.schema.number().int().min(1).max(50).optional(),
  },
  async execute(args, context) {
    requirePm(context);
    if (args.action === "status") return runProgram("Git status", "git", ["status", "--short"], 120000, context.abort);
    if (args.action === "log") {
      return runProgram("Git log", "git", ["log", "--oneline", "-n", String(args.limit || 20)], 120000, context.abort);
    }
    if (args.action === "head") return runProgram("Git HEAD", "git", ["rev-parse", "HEAD"], 120000, context.abort);
    const argv = ["diff"];
    if (args.staged) argv.push("--cached");
    const paths = (args.paths || []).map(safeGitPath);
    if (paths.length) argv.push("--", ...paths);
    return runProgram("Git diff", "git", argv, 120000, context.abort);
  },
});

const harnessPmWrite = tool({
  description:
    "Write only PM-owned durable documentation. Allowed: docs/**, harness/memory/**, and harness/specs/README.md. Task-package role artifacts and source code are always rejected.",
  args: {
    path: tool.schema.string(),
    content: tool.schema.string().max(500000),
  },
  async execute(args, context) {
    requirePm(context);
    const target = safePmWritePath(args.path);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, args.content, "utf8");
    const relative = path.relative(root, target).replaceAll("\\", "/");
    return {
      title: "Harness PM document written",
      output: JSON.stringify({ ok: true, path: relative, bytes: Buffer.byteLength(args.content, "utf8") }, null, 2),
      metadata: { ok: true, path: relative },
    };
  },
});

return async () => ({
  tool: {
    harness_change: harnessChange,
    harness_git_read: harnessGitRead,
    harness_pm_write: harnessPmWrite,
  },
  "chat.message": async (input) => {
    if (input?.sessionID && input?.agent) sessionAgents.set(input.sessionID, input.agent);
  },
  "chat.params": async (input) => {
    if (input?.sessionID && input?.agent) sessionAgents.set(input.sessionID, input.agent);
  },
  "tool.execute.before": async (input, output) => {
    if (toolName(input) !== "task" || sessionAgents.get(input?.sessionID) !== "harness-pm") return;
    const role = requestedTaskRole(output?.args);
    if (!allowedRoles.has(role)) {
      throw new Error(`Harness PM may only dispatch registered Harness Workers; received: ${role || "unknown"}`);
    }
    const observation = {
      agent_id: `opencode-${input?.sessionID || "session"}-${Date.now()}`,
      role,
      input,
      task_args: output?.args,
    };
    activeTasks.set(taskObservationKey(input), observation);
    await dispatchObservation(observation, "start");
  },
  "tool.execute.after": async (input, output) => {
    if (toolName(input) !== "task") return;
    const key = taskObservationKey(input);
    const observation = activeTasks.get(key);
    activeTasks.delete(key);
    if (!observation) return;
    await dispatchObservation({ ...observation, input, output }, "stop").catch(() => {
      // Task completion evidence transport is fail-open and never delays the Task return.
    });
  },
});
}
