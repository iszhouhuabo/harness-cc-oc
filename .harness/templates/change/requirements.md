# 需求规格

<!-- harness-document: requirements@3 -->

## Actors

| Actor ID | 角色 | 目标 | 权限/约束 |
| --- | --- | --- | --- |
| ACT-001 | <角色> | <期望结果> | <业务边界> |

## Requirement Delta

| Requirement | 状态 | 来源 Delta/旧 ID | 变化与依据 |
| --- | --- | --- | --- |
| REQ-001 | new/changed/unchanged/deprecated | DELTA-001 / <旧 REQ> | <中文说明> |

修订时保留未被明确替换的旧 ID；changed/deprecated 必须指向旧需求，不能只写“已调整”。

## Requirements

### REQ-001: <中文需求名称>

- Actor: ACT-001
- Source: DELTA-001 / DEC-001
- Priority: MUST/SHOULD/COULD
- Rule: 系统 SHALL <只描述可观察业务行为，不写框架、文件、API、Schema 或路由>。

#### REQ-001-SC-001 Scenario: <正常场景>

- Given <可复现前置条件>
- When <动作或事件>
- Then <可观察结果>
- And <需要时补充结果；没有则删除本行>

#### REQ-001-SC-002 Scenario: <异常/权限/边界场景>

- Given <前置条件>
- When <失败、越权或边界动作>
- Then <错误反馈、状态和不可发生事项>

## Non-Goals

- <本轮明确不承诺的能力；没有时写“无”>

## Constraints

| Constraint ID | 业务/合规/兼容约束 | 来源 | 验收方式 |
| --- | --- | --- | --- |
| CON-001 | <约束；没有时写 N/A> | <来源> | <如何观察> |

## Blocking Questions

| ID | 问题 | Owner | 影响的 Requirement/Scenario |
| --- | --- | --- | --- |
| BA-001 | <没有时整节写“无”> | PM/user | <REQ/SC> |

## Conclusion

PASS / BLOCK
