# 任务清单

<!-- harness-document: tasks@3 -->

## Task Delta

| Task ID | 状态 | 本轮处理 | 旧证据/影响依据 | 本轮复核要求 |
| --- | --- | --- | --- | --- |
| TASK-DEV-001 | pending/done | new/reset/carried_forward/deprecated | <commit/test/path/reason> | <Dev/CR/TE 如何复核> |

`carried_forward` 只保留有证据且未受影响的实现事实，不恢复旧阶段 PASS；证据不足或误判完成必须 reset。

## Checklist Ownership

| Owner | 可更新内容 | 禁止事项 |
| --- | --- | --- |
| SA | Task 定义、映射、初始状态、Delta 分类 | 不勾选 Dev/CR/TE 本轮完成 |
| Dev | Dev-owned 状态与实现证据 | 不改任务定义或 CR/TE 状态 |
| CR | CR-owned 状态与审查证据 | 不改代码或 Dev/TE 状态 |
| TE | TE-owned 状态与测试证据 | 不改生产代码或 Dev/CR 状态 |

## Requirement Traceability

| Task ID | Requirement/Scenario | Design ID | Owner | Evidence Required |
| --- | --- | --- | --- | --- |
| TASK-DEV-001 | REQ-001-SC-001 | DES-001 | Dev | <code/test/command> |

## Implementation

- [ ] TASK-DEV-001 — <动作>；Input: <输入>；Output: <输出>；Acceptance: <验收>；Evidence: <要求>

## Review

- [ ] TASK-CR-001 — 审查 <范围>；关联 TASK/REQ: <IDs>；Evidence: CHK-CR + findings

## Verification

- [ ] TASK-TE-001 — 验证 <Scenario/回归/gate>；关联: <IDs>；Evidence: CHK-TE + command/artifact

## Documentation And Closeout

- [ ] TASK-DOC-001 — 更新 <长期规格/用户文档/迁移说明；不适用写 N/A>
- [ ] TASK-CLOSE-001 — 清理临时产物、确认风险和归档输入

## Conclusion

PASS / BLOCK
