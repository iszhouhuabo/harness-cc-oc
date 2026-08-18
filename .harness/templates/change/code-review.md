# Code Review

<!-- harness-document: code-review@3 -->

## Inputs

| 输入 | 版本/范围 | 结论/状态 |
| --- | --- | --- |
| requirements/design/tasks/readiness/dev-log | <ID/time> | <checked> |

## Reviewed Diff

| 项目 | 值 |
| --- | --- |
| Base/Head | <commit/range> |
| Changed Files | <实际文件清单> |
| User Existing Changes | <如何区分> |

## Checklist Results

逐项对应 `.harness/checklists/code-review.md`，不得省略适用项。

| Check ID | 名称 | Severity | Result | Finding ID | Evidence | Notes/N/A 理由 |
| --- | --- | --- | --- | --- | --- | --- |
| CHK-CR-001 | 编译构建阻塞检查 | P0 | PASS/FAIL/N/A | CR-001/- | <证据> | <说明> |
| CHK-CR-002 | 需求覆盖检查 | P0 | PASS/FAIL/N/A | CR-002/- | <证据> | <说明> |
| CHK-CR-003 | 方案一致性检查 | P0 | PASS/FAIL/N/A | CR-003/- | <证据> | <说明> |
| CHK-CR-004 | 范围外修改检查 | P1 | PASS/FAIL/N/A | CR-004/- | <证据> | <说明> |
| CHK-CR-005 | 测试匹配检查 | P1 | PASS/FAIL/N/A | CR-005/- | <证据> | <说明> |
| CHK-CR-006 | 证据可信度检查 | P0 | PASS/FAIL/N/A | CR-006/- | <证据> | <说明> |
| CHK-CR-007 | 安全与数据风险检查 | P0 | PASS/FAIL/N/A | CR-007/- | <证据> | <说明> |
| CHK-CR-008 | 角色边界检查 | P0 | PASS/FAIL/N/A | CR-008/- | <证据> | <说明> |

## Findings

| Finding ID | Severity | Owner | File/Line | Evidence | Impact | Required Fix |
| --- | --- | --- | --- | --- | --- | --- |
| CR-001 | P0/P1/P2/P3 | Dev-owned/TE-owned/Upstream-contract | `<path:line>` | <事实> | <影响> | <修复要求> |

没有 finding 时写“无”，不要保留示例行。

## Evidence Review

| Dev Evidence/Gate | 与当前 diff 同轮 | 可复现 | Review Result |
| --- | --- | --- | --- |
| <command/artifact> | yes/no | yes/no | PASS/FAIL |

## Ownership And Return Route

| Owner | Finding IDs | PM Route | Required Re-review |
| --- | --- | --- | --- |
| Dev/TE/BA/SA/PM-user | <IDs> | <下一角色> | CR required/N/A |

CR 不修改实现。修复完成后由新的 CR Task 重新验证 finding。

## Reusable Experience Draft

REJECT 或发现可复发问题时按“症状、根因、修复、防复发/检测”记录；没有写“无”。

## Conclusion

PASS / REJECT
