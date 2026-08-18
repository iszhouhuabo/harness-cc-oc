---
name: code-review
description: 对当前任务的实际 diff 做独立、只读代码审查，并将需求、设计、任务和测试证据逐项追踪到发现。CR 阶段或修复后重新评审时使用；CR 不修改实现，发现问题必须给出 Owner 和确定性回退。
---

# Code Review

## Inputs

- CR 角色契约、`requirements.md`、`design.md`、`tasks.md`、`readiness-review.md`。
- `dev-log.md`、当前 Git diff、基线差异及实际测试文件。
- `.harness/checklists/code-review.md`；必须逐项写入 `code-review.md`。

## Procedure

1. 确认审查的是当前工作区真实 diff，而不是 Dev 摘要中的文件清单。
2. 建立 `Requirement/Scenario → Design → Task → Diff → Test` 追踪；标记遗漏和范围外修改。
3. 从外部接口和关键业务路径开始，再检查错误处理、状态变化、事务/并发、兼容性和可维护性。
4. 检查鉴权、授权、输入校验、敏感信息、数据迁移、日志和外部连接风险。
5. 检查测试是否真正断言新行为、是否能在缺陷存在时失败，以及证据是否来自当前轮次。
6. 逐项完成 CHK-CR-001 至 CHK-CR-008；不适用项写事实依据。
7. 每个 finding 写精确位置、严重度、证据、影响、Owner 和 Required Fix；不要写模糊建议。
8. 根据最高严重度和 Owner 给出唯一结论；修复后重新读取新 diff 并完整复审受影响项。

## Decision Rules

- `PASS`：所有适用 Checklist 通过，且没有开放的 P0/P1 finding。
- `REJECT`：存在实现、测试、证据、范围、安全或上游契约阻塞。
- Owner=Developer：实现、代码测试或 Dev 证据问题，回 Dev 后重新 CR。
- Owner=Test Engineer：独立验收资产或 TE 专属准备问题，交 TE；代码仍由 Dev 修改。
- Owner=Business Analyst/Solution Architect：需求或方案问题，退出 apply 并重新走上游与 RR。
- CR 不得为了让评审通过而修改任何生产代码、测试、配置或上游产物。

## Output Contract

在 `code-review.md` 中完整填写：Inputs、Diff Scope、Traceability、Checklist Results、Findings、Evidence、Return Route、Memory Draft、Conclusion。

收工前确保每个失败 Checklist 都关联 finding，每个 finding 都有唯一 Owner；聊天结论不能替代报告。
