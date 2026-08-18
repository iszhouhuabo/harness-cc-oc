# 方案设计

<!-- harness-document: design@3 -->

## Inputs And Constraints

| 输入 | 版本/ID | 约束摘要 |
| --- | --- | --- |
| proposal/requirements/impact-analysis | <ID/time> | <必须遵守的边界> |

## Design Delta

| Design ID | Requirement/Scenario | 状态 | 旧设计/路径 | 本轮变化 |
| --- | --- | --- | --- | --- |
| DES-001 | REQ-001, REQ-001-SC-001 | new/changed/unchanged/deprecated | <旧 ID/path 或 N/A> | <中文说明> |

## Requirement Mapping

| Requirement/Scenario | Design ID | Task ID | Test Owner | 未覆盖理由 |
| --- | --- | --- | --- | --- |
| REQ-001-SC-001 | DES-001 | TASK-DEV-001 | Dev/TE | <完整覆盖时写“-”> |

## Architecture

### DES-001: <设计项名称>

- Boundary: <模块/责任边界>
- Flow: <调用、事件或数据流>
- Failure Behavior: <错误、超时、重试、事务或降级>
- Security: <鉴权、授权、敏感数据；不适用写 N/A>

## Interfaces And Data

| Interface/Data ID | 输入 | 输出 | 兼容性 | 错误语义 |
| --- | --- | --- | --- | --- |
| IF-001 | <契约> | <契约> | backward-compatible/breaking/N/A | <错误行为> |

## Decisions

| Decision ID | 选择 | 依据 | 被放弃方案 | 取舍 |
| --- | --- | --- | --- | --- |
| SA-DEC-001 | <选择> | <REQ/repo evidence> | <方案> | <影响> |

## Impact

| 模块/路径 | 修改类型 | Design/Requirement | 风险 |
| --- | --- | --- | --- |
| `<path>` | add/change/remove | DES-001 / REQ-001 | <风险> |

## Task Plan

| Task ID | Owner | 输入 | 输出 | 验收 | 依赖 |
| --- | --- | --- | --- | --- | --- |
| TASK-DEV-001 | Dev | DES-001 | <code/test> | <可验证结果> | <Task/N/A> |

## Test Ownership

| Requirement/Scenario/Gate | Dev 负责 | TE 负责 | 不适用理由 |
| --- | --- | --- | --- |
| REQ-001-SC-001 | <unit/component> | <E2E/regression> | <N/A> |

## Verification Contract

| Gate ID | Gate | Runtime Requirement | Working Directory | Command argv | Owner | N/A 理由 |
| --- | --- | --- | --- | --- | --- | --- |
| GATE-001 | runtime/compile/unit/integration/build/startup/smoke/database | <project pin> | `.` | `<executable> <args>` | Dev/TE | <不适用时说明> |

先用兼容 JDK 8+ 的 `java -version`、`python --version`、`node --version` 或项目等价命令证明实际版本。compile/build/test 不能冒充 startup、smoke 或 database gate。

## Compatibility Migration And Rollback

| 项目 | 策略 | 执行前置 | 回滚触发 | 回滚步骤 |
| --- | --- | --- | --- | --- |
| API/data/config/deploy | <策略或 N/A> | <前置> | <条件> | <步骤> |

## Risks

| Risk ID | 风险 | 监测 | 缓解 | Owner |
| --- | --- | --- | --- | --- |
| RISK-001 | <风险> | <信号> | <措施> | <Owner> |

## Unresolved Branches

| ID | 未决分支 | Owner | 对实现/验收影响 |
| --- | --- | --- | --- |
| SA-001 | <没有时整节写“无”> | BA/SA/PM-user | <影响> |

## Readiness Self-Check

quick profile 逐项填写完整性、需求纯净度、映射覆盖、任务可执行性、验证契约和开放分支，最后写 PASS/BLOCK；standard/refactor 写 `N/A，由 RR 独立评审`。

## Conclusion

PASS / BLOCK
