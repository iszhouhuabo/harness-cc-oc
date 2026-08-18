# Test Report

<!-- harness-document: test-report@5 -->

## Inputs

| 输入 | 版本/范围 | 状态 |
| --- | --- | --- |
| requirements/design/tasks/dev-log/code-review/diff | <ID/time/range> | <checked> |

## Environment And Evidence

| 项目 | 实际值 | 证据/说明 |
| --- | --- | --- |
| Runtime/dependencies/services/data | <版本/地址/状态> | <命令、健康检查或配置来源> |
| Evidence form | runner report/assertion/API/DB/log/script/manual observation | <位置或摘要；不要求截图> |
| Maven reactor scope | scoped_without_am / also_make / N/A | <上游模块、父 POM/公共配置、SNAPSHOT、跨模块影响检查；不得默认添加 -am> |
| Vue/Node/Python execution scope | targeted_runner / expanded_gate / N/A | <runner、目标集合；build/全量/tox-nox矩阵/coverage 的明确适用原因> |

## Verification Inputs

列出会使本轮 TE 证据失效的生产代码、TE-owned 测试资产、模块目录和构建/测试配置；必须覆盖 Dev Changed Files，范围外用户改动只记录 warning。

| Path | Purpose |
| --- | --- |
| `<file-or-bounded-directory>` | task source / TE-owned asset / build config / dependency input |

## Checklist Results

逐项对应 `.harness/checklists/test-engineering.md`，不得省略适用项。

| Check ID | 名称 | Severity | Result | Failure ID | Evidence | Notes/N/A 理由 |
| --- | --- | --- | --- | --- | --- | --- |
| CHK-TE-001 | 可复现验证证据检查 | P0 | PASS/FAIL/N/A | TE-001/- | <证据> | <说明> |
| CHK-TE-002 | 验收场景覆盖检查 | P0 | PASS/FAIL/N/A | TE-002/- | <证据> | <说明> |
| CHK-TE-003 | 编译构建验证检查 | P0 | PASS/FAIL/N/A | TE-003/- | <证据> | <说明> |
| CHK-TE-004 | 启动与冒烟检查 | P0 | PASS/FAIL/N/A | TE-004/- | <证据> | <说明> |
| CHK-TE-005 | 数据库与迁移检查 | P0 | PASS/FAIL/N/A | TE-005/- | <证据> | <说明> |
| CHK-TE-006 | 回归范围检查 | P1 | PASS/FAIL/N/A | TE-006/- | <证据> | <说明> |
| CHK-TE-007 | 环境归属检查 | P1 | PASS/FAIL/N/A | TE-007/- | <证据> | <说明> |
| CHK-TE-008 | 角色边界检查 | P0 | PASS/FAIL/N/A | TE-008/- | <证据> | <说明> |

## Test Matrix

### Class Coverage Summary

四类是覆盖分类，不是四条独立命令；同一执行结果可以映射多个 Class，但每类必须有结论。

| Class | 必需覆盖 | Result | Test IDs/Evidence | N/A/选择理由 |
| --- | --- | --- | --- | --- |
| A | 当前任务直接接口、API、组件、函数或任务入口 | PASS/FAIL/N/A | <IDs/证据> | <理由> |
| B | 当前任务适用 GWT 的真实可执行验收链路 | PASS/FAIL/N/A | <IDs/证据> | <理由> |
| C | standard/refactor 选择 1–2 个最相关历史场景 | PASS/FAIL/N/A | <IDs/证据> | <选择依据/人工全量入口> |
| D | 一次最低必要工程验证及适用 baseline/post-verify | PASS/FAIL/N/A | <IDs/证据> | <理由> |

| Test ID | Class | Requirement/Scenario/Gate | Runtime Actual | Working Directory | Command/Steps | Verification Scope | Result | Exit Code | Evidence | N/A 理由 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TEST-001 | A/B/C/D | REQ-001-SC-001 / GATE-001 | <实际版本> | `.` | `<executable> <args>` | project / reactor_scope=scoped_without_am / reactor_scope=also_make / execution_scope=targeted_runner / execution_scope=expanded_gate:<原因> | PASS/FAIL/N/A | <code> | <关键输出；文件用 file:<项目内路径>> | <说明> |

Command/Steps 中的自动化 PASS 行只写单一 argv，Exit Code 必须为 0，Evidence 必须是非空、非占位的实际输出/日志；人工步骤写 N/A 与证据。Java 使用满足当前任务的最低必要生命周期：无制品、打包或集成阶段要求时只记录一次 `./mvnw test` 或 `./gradlew test`，不先记录 compile，也不自动升级 package/verify/build。Maven `-pl` 在目标模块独立且上游 artifact 一致性可证明时使用 `scoped_without_am` 并省略 `-am`；上游/POM/SNAPSHOT/跨模块风险存在时使用 `also_make`。TE 必须独立执行 D 类工程验证，不复用 Dev 的 Maven 结果。正常 delivery 只审计本表，不重放命令；`--replay` 仅供人工诊断。

同一 runner、工作目录、模块/profile 下可安全合并的目标只启动一次进程；A/B/C/D 可以复用同一结果映射。上下文压缩、Worker 重入、CR 或 delivery 不是重跑理由。证据可为 runner 报告、断言输出、API/数据库结果、日志或持久化脚本，不要求截图；引用文件时必须真实存在。

Vue/Node 的 test 与 build 是不同 gate，但 build 仅在 Verification Plan 明确要求生产 bundle、类型/构建配置或产物验证时执行；Vitest/Jest/Playwright/ESLint 明确目标合并为一次。Python 只选 pytest、unittest、tox、nox 或项目脚本之一；不得先跑 pytest/unittest 再跑覆盖相同目标的 tox/nox，不默认全量、多解释器、coverage、依赖重装或 collect-only。TE 必须独立执行，不复用 Dev 结果。

Class A=当前接口/组件，B=本轮 GWT 真实验收链路，C=1–2 个相关历史场景，D=最低必要工程验证/post-verify；分类不等于命令数量。

## Requirement Coverage

| Requirement/Scenario | Test IDs | Result | Evidence | Gap/Risk |
| --- | --- | --- | --- | --- |
| REQ-001-SC-001 | TEST-001 | PASS/FAIL/N/A | <证据> | <gap 或 -> |

## Regression And Baseline

| 范围 | Baseline | Current | 新增失败 | 结论 |
| --- | --- | --- | --- | --- |
| affected/history/full | <引用/数量> | <结果> | <数量与 IDs> | PASS/FAIL |

## Persisted Test Assets

| Asset ID | Path | 覆盖 Scenario | 本轮动作 | 复现方式 |
| --- | --- | --- | --- | --- |
| ASSET-001 | `<path>` | REQ-001-SC-001 | add/update/reuse/N/A | <command/steps> |

## Failures

| Failure ID | Severity | Owner | Related IDs | Evidence | Reproduction | Required Fix |
| --- | --- | --- | --- | --- | --- | --- |
| TE-001 | P0-P3 | Dev-owned/TE-owned/Upstream-contract/Environment | <REQ/TASK/CHK> | <证据> | <步骤> | <下一步> |

没有 failure 时写“无”，不要保留示例行。

## Reusable Experience Draft

FAIL/BLOCK 或发现可复发问题时按“症状、根因、修复、防复发/检测”记录；没有写“无”。

## Conclusion

PASS / FAIL / BLOCK
