# 就绪评审

<!-- harness-document: readiness-review@3 -->

## Reviewed Inputs

| 文件 | Schema/版本/时间 | 结论 | 是否晚于上次评审 |
| --- | --- | --- | --- |
| proposal/requirements/design/tasks/impact-analysis | <值> | PASS/BLOCK | yes/no/N/A |

## Checklist Results

| Check ID | 检查项 | Severity | Result | Evidence | Finding ID | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| RR-CHK-001 | 文档 schema、必要章节、稳定 ID、模板残留 | P1 | PASS/FAIL/N/A | <证据> | RR-001/- | <说明> |
| RR-CHK-002 | Requirement Delta 可定位且增量内容未误删 | P0 | PASS/FAIL/N/A | <证据> | RR-002/- | <说明> |
| RR-CHK-003 | SHALL/GWT 业务纯净、可测试、覆盖关键路径 | P0 | PASS/FAIL/N/A | <证据> | RR-003/- | <说明> |
| RR-CHK-004 | Requirement/Scenario → Design → Task 追踪完整 | P0 | PASS/FAIL/N/A | <证据> | RR-004/- | <说明> |
| RR-CHK-005 | 影响面、兼容、迁移、回滚和风险完整 | P1 | PASS/FAIL/N/A | <证据> | RR-005/- | <说明> |
| RR-CHK-006 | Task 有 Owner、输入、输出、验收和证据要求 | P0 | PASS/FAIL/N/A | <证据> | RR-006/- | <说明> |
| RR-CHK-007 | Test Ownership 与 Verification Contract 可执行 | P0 | PASS/FAIL/N/A | <证据> | RR-007/- | <说明> |
| RR-CHK-008 | 无下游代替上游做未授权决策 | P0 | PASS/FAIL/N/A | <证据> | RR-008/- | <说明> |

## Traceability Review

| Requirement/Scenario | Design | Task | Test Owner | Result | Gap/Finding |
| --- | --- | --- | --- | --- | --- |
| REQ-001-SC-001 | DES-001 | TASK-DEV-001 | Dev/TE | PASS/FAIL | <gap 或 -> |

## Findings

| Finding ID | Severity | Owner | File/Section | Evidence | Required Fix |
| --- | --- | --- | --- | --- | --- |
| RR-001 | P0/P1/P2/P3 | BA/SA/PM-user | `<file#section>` | <事实> | <修复要求> |

没有 finding 时写“无”，不要保留示例行。

## Ownership And Return Route

| Owner | Finding IDs | PM 下一步 | 重新 RR |
| --- | --- | --- | --- |
| BA/SA/PM-user | <IDs> | <返回动作> | required/N/A |

RR 不修改 BA/SA 文件。任何 BA/SA 修订后都必须重新 RR，不能由 PM 确认替代。

## Reusable Experience Draft

可复发且已验证的问题按“症状、根因、修复、防复发/检测”记录；没有写“无”。草稿缺失不改变 RR 质量结论。

## Conclusion

PASS / BLOCK
