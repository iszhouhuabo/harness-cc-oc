---
name: test-e2e
description: 从需求 Scenario 建立并执行跨组件、API、页面、数据库或任务链路的独立验收。TE 阶段、修复回归或关键用户流程变更时使用；要求可复现环境、确定数据、覆盖矩阵、失败归属和最终证据。
---

# End-to-end Testing

## Inputs

- TE 角色契约、`requirements.md`、`design.md`、`tasks.md`、`code-review.md`。
- `dev-log.md` 中的运行入口和验证证据、当前构建产物及测试环境事实。
- `.harness/checklists/test-engineering.md` 和 `test-report.md` 模板。

## Procedure

1. 从每个 SHALL 和 Given/When/Then Scenario 建立 A/B/C/D 覆盖矩阵，禁止只测试 Dev 声称改动的路径。四类是覆盖分类，不是四条独立命令；每类必须 PASS/FAIL 或有事实依据的 N/A。
2. B 类覆盖当前任务每个适用 GWT 的真实可执行链路；可使用 API、CLI、任务、数据库或 UI。UI 只在需求明确且环境具备浏览器能力时使用，不要求截图，不强制 Playwright。
3. C 类在 standard/refactor 中最多选择 1–2 个与改动影响面直接相关的历史场景；不默认全量。超过预算时记录选择依据和建议的人工全量入口。
4. D 类由 TE 独立执行满足当前任务最低必要生命周期的一次工程验证并执行适用 baseline/post-verify，不复用 Dev 的命令结果；同一 TE 测试命令已覆盖 A/B/C/D 时复用结果映射，不再次启动进程。Maven `-pl` 先判定 `scoped_without_am|also_make`，不得默认添加 `-am`；Vue/Node/Python 先判定 `targeted_runner|expanded_gate`，不得默认 build、全量、多解释器、tox/nox矩阵或 coverage。
5. 为每个场景明确前置数据、身份/权限、操作步骤、期望结果、清理方式和证据类型；可执行 GWT 与持久化用例/脚本按 ID 或测试名 1:1 对照。
6. 记录运行时、依赖、服务地址、数据库版本和关键配置；敏感值只记录来源，不写入报告。先验证环境健康和主路径，再执行适用的权限、失败反馈、边界和兼容场景。
7. 优先合并同一 runner、工作目录、模块/profile 下可安全合并的目标，整批只启动一次进程；无法证明等价时才拆分并记录原因。上下文压缩、Worker 重入、CR 或 delivery 不是重跑理由。
8. 使用真实用户/API/数据库/任务链路；mock 只能覆盖 design 允许隔离的边界。证据可以是 runner 报告、断言输出、API/数据库结果、日志或持久化脚本，不要求截图；声明证据文件时必须真实存在。
9. 失败先稳定复现，再加载 `systematic-debug` 判定 Owner；TE 不修改生产代码或 Dev-owned 单元/组件测试，但可修复 TE-owned E2E/cases/验收脚本。修复后只重跑失败目标及受影响相关场景。
10. 完成 CHK-TE-001 至 CHK-TE-008，并运行 `harness.py delivery <task> --role test-engineer` 审计本轮已执行证据；正常 delivery 不重放命令，`--replay` 仅供人工诊断。

## Coverage And Routing

- 主路径：用户目标端到端可完成。
- 权限路径：未授权、越权、会话失效和角色差异行为正确。
- 失败路径：输入错误、依赖失败、超时和重试反馈符合需求。
- 数据路径：初始化、迁移、持久化、幂等和清理可验证。
- 回归路径：受影响相邻能力及历史高风险点没有退化。
- 执行预算：覆盖分类不得机械展开为四次命令；C 类最多 1–2 个相关历史场景，不默认全量测试或全量 E2E。
- 实现失败：Owner=Developer，修复后必须重新 CR → TE。
- 需求/设计偏差：Owner=BA/SA，退出 apply，重新 propose 和 RR。
- 环境失败：必须有环境健康对照和证据；修复环境后由同一 TE 任务或明确重派继续。

## Decision Rules

- `PASS`：所有适用 Scenario 和 Checklist 通过，没有开放阻塞失败。
- `FAIL`：任一必需场景失败、覆盖缺口无合理 N/A、证据不可复现或环境归属未证明。
- `N/A` 必须逐项说明事实依据，不能用“无法测试”代替。

## Output Contract

在 `test-report.md` 中填写：环境与证据方式、A/B/C/D Coverage Summary、Test Matrix、回归与基线、Persisted Test Assets、Failures 和 Conclusion。每个 Scenario 必须能追溯到可执行用例/步骤和证据或明确 N/A；不要求截图，但引用的证据文件必须存在。
