---
name: post-verify
description: 在代码或测试资产修改后，以实际 diff 和修改前基线重新验证受影响范围。Dev 修复完成、CR 要核验证据或 TE 做最终回归时使用；用于发现漏测、陈旧证据和本次新增失败。
---

# Post-change Verification

## Inputs

- `baseline.json`、当前 Git diff 和工作区状态。
- `requirements.md` 的 SHALL/Scenario、`design.md` 的 Verification Plan。
- 本轮实际执行过的命令及当前角色报告。

## Procedure

1. 按宿主系统运行 baseline compare：Windows 使用 `py -3 .harness/scripts/harness.py baseline <task> compare`；macOS/Linux 使用 `python3 .harness/scripts/harness.py baseline <task> compare`。确认基线存在并保存差异摘要，不让用户轮流试探 Python 入口。
2. 重新读取实际 diff，按模块、行为、配置、依赖、迁移和测试资产分类。
3. 将每类改动映射到 Requirement/Scenario、设计验证项及原验证命令；发现未覆盖改动时补入验证计划。
4. 先重跑最小相关检查，再执行受影响回归；不得引用修改前或上轮修复前的 PASS。
5. 涉及服务、页面、API、数据库、鉴权、迁移或定时任务时，执行对应真实链路验证。
6. 对比修改前后失败：标记 `pre-existing`、`introduced`、`resolved`，并为每项提供证据。
7. 将最终命令、工作目录、退出码、输出摘要和基线分类写入 `dev-log.md` 或 `test-report.md`。
8. 由 Dev/TE Hook 或 PM fallback 运行 `harness.py delivery <task> --role <role>`，只审计本轮报告证据，不重复执行构建/测试。`--replay` 仅用于人工诊断明确复现，正常 apply、Hook 和 PM fallback 禁止使用。
9. delivery PASS 结果必须绑定当前 task、role、`mode=evidence_audit`、报告 SHA-256、baseline SHA-256、`Verification Inputs` 和其作用域指纹；报告、任务轮次或作用域内源码/配置/测试资产之后发生变化都必须重新审计。范围外工作区变化只进入 warning，不阻断 apply-close；显式 `file:`/Markdown 文件证据必须存在且非空。

## Failure Branches

- 命令稳定失败：进入 `systematic-debug`，先定位再修复。
- 证据已过期：重新执行，不允许复制旧 PASS。
- diff 越出 Scope：Dev 停止扩展；CR 标记 Owner=Developer 并 REJECT。
- 上游漏掉验证契约：报告 Owner=Solution Architect，不能由当前角色静默改设计。
- Hook 未运行或结果丢失：PM 只补跑一次相同 `harness.py delivery`；Hook 运输故障只记 DEGRADED。

## Completion Criteria

- 所有当前 diff 均映射到验证项。
- 所有适用命令在当前轮次实际执行。
- 没有新增未解释失败。
- 报告包含可由 `harness.py` 解析的命令、目录和结果。
- 报告的 `Verification Inputs` 有界且覆盖本轮验证依赖；范围外用户改动没有被错误纳入证据身份。
- delivery 返回 `mode=evidence_audit` 且 `checks=[]`；项目命令已经由当前 Worker 执行，不由 delivery 代跑。
- 结论只能是角色契约允许的单一值，不保留模板占位文本。
