# Dev Log

<!-- harness-document: dev-log@5 -->

## Baseline And Scope

| 项目 | 值 | 证据 |
| --- | --- | --- |
| Entry git status/diff | <摘要> | <command/commit> |
| Allowed scope | <paths/tasks> | <TASK/DES IDs> |
| User existing changes | <paths 或无> | <如何保护> |

## Implementation Records

| Record ID | Task/REQ/DES | 动作 | 结果 | 设计偏差 |
| --- | --- | --- | --- | --- |
| DEV-IMP-001 | TASK-DEV-001 / REQ-001 / DES-001 | <实现摘要> | done/partial | none / <已批准偏差> |

## Changed Files

| 文件 | Record/Task ID | 变更摘要 | 风险/备注 |
| --- | --- | --- | --- |
| `<path>` | DEV-IMP-001 / TASK-DEV-001 | <中文说明> | <风险或无> |

## Verification Inputs

列出会使本轮 Dev 证据失效的任务文件、模块目录和构建/测试配置；用户并行改动但与这些路径无交集时只记录 warning。

| Path | Purpose |
| --- | --- |
| `<file-or-bounded-directory>` | task source / Dev-owned test / build config / dependency input |

## Task Checklist Updates

| Task ID | 进入状态 | 本轮状态 | Evidence | carried_forward 复核 |
| --- | --- | --- | --- | --- |
| TASK-DEV-001 | pending/done/carried_forward | done/pending/blocked | <file/test/command> | confirmed/reset/N/A |

## Verification Plan

| Gate ID | Runtime Requirement | Working Directory | Command argv | 适用性来源 |
| --- | --- | --- | --- | --- |
| GATE-001 | <project pin> | `.` | `<executable> <args>` | design Verification Contract |

Maven `-pl` 额外记录：`reactor_scope=scoped_without_am|also_make`；附 baseline/current diff、上游模块、父 POM/公共配置、SNAPSHOT 与跨模块影响检查。不得默认添加 `-am`。

Vue/Node/Python 额外记录：`execution_scope=targeted_runner|expanded_gate`、选用 runner、目标集合及 expanded_gate 原因。Node build、Python 全量/tox/nox 矩阵/coverage 不得默认执行，同一覆盖集不得重复运行。

不得擅自删除或降低 SA 定义的 gate；需要改变契约时 BLOCK 回 SA。

## Verification Results

| Gate ID | Gate | Runtime Actual | Working Directory | Command | Verification Scope | Result | Exit Code | Evidence | N/A 理由 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GATE-001 | runtime/compile/unit/integration/build/startup/smoke/database | <实际版本> | `.` | `<executable> <args>` | project / reactor_scope=scoped_without_am / reactor_scope=also_make / execution_scope=targeted_runner / execution_scope=expanded_gate:<原因> | PASS/FAIL/N/A | <code> | <关键输出；文件用 file:<项目内路径>> | <不适用时说明> |

Command 只写单一 argv；每条 PASS 的 Exit Code 必须为 0，Evidence 必须是非空、非占位的实际输出/日志。Java 使用满足当前任务的最低必要生命周期：无制品、打包或集成阶段要求时只记录一次 `./mvnw test` 或 `./gradlew test`，不先记录 compile，也不自动升级 package/verify/build。Maven `-pl` 在目标模块独立且上游 artifact 一致性可证明时使用 `scoped_without_am` 并省略 `-am`；上游/POM/SNAPSHOT/跨模块风险存在时使用 `also_make`。Vue/Node 的 test 与 build 可作为不同 gate 各执行一次。正常 delivery 只审计本表，不重放命令；`--replay` 仅供人工诊断。

## Post-change Review

| Check | Result | Evidence/Notes |
| --- | --- | --- |
| 实际 diff 与 Scope/Tasks 一致 | PASS/FAIL | <证据> |
| 无调试残留、意外生成物或敏感信息 | PASS/FAIL | <证据> |
| 测试、配置、文档和 checklist 同步 | PASS/FAIL/N/A | <证据> |
| 用户已有改动未被覆盖 | PASS/FAIL | <证据> |

## Open Items

| ID | Severity | Owner | Status | Evidence | Next Step |
| --- | --- | --- | --- | --- | --- |
| DEV-001 | P0-P3 | Dev/BA/SA/Environment/PM-user | OPEN/CLOSED/N/A | <证据> | <下一步> |

## Reusable Experience Draft

出现 BLOCK、返工或可复发工程坑时，按“症状、根因、修复、防复发/检测”记录；一次通过且无复用价值时写“无”。

## Conclusion

PASS / BLOCK
