# 影响面分析

<!-- harness-document: impact-analysis@3 -->

## Scope

- Task: <change-id>
- Proposal Delta: <DELTA IDs>
- Analysis Boundary: <本次扫描范围与明确未扫描范围>

## Baseline

| Baseline ID | 类型 | 证据 | 当前状态 |
| --- | --- | --- | --- |
| BASE-001 | git/spec/test/runtime | <commit/path/command> | clean/known-dirty/unknown |

## Impact Matrix

| Impact ID | 规格域/模块 | 影响类型 | 证据 | 风险 | Owner |
| --- | --- | --- | --- | --- | --- |
| IMP-001 | <scope> | direct/indirect/none | <path/spec/symbol> | high/medium/low | BA/SA/Dev/TE |

## Affected Specs

| Spec/Requirement | 影响 | 预期 Delta | 证据 |
| --- | --- | --- | --- |
| <path/REQ> | add/change/remove/unchanged | <中文说明> | <引用> |

## Affected Code Areas

| 模块/路径/符号 | 影响原因 | 兼容风险 | 预计验证 |
| --- | --- | --- | --- |
| `<path or symbol>` | <原因> | <风险> | <gate> |

## Compatibility And Migration

| 项目 | 是否适用 | 策略 | 回退 |
| --- | --- | --- | --- |
| API/data/config/deployment | yes/no | <兼容或迁移> | <回退> |

## Split Recommendation

- Decision: single-task / split / PM-user-decision
- Reason: <范围、依赖和风险依据>
- Proposed Split: <不拆分写 N/A>

## Risks

| Risk ID | 风险 | 概率/影响 | 缓解 | Owner |
| --- | --- | --- | --- | --- |
| RISK-001 | <风险> | <值> | <措施> | <Owner> |

## Conclusion

PASS / BLOCK
