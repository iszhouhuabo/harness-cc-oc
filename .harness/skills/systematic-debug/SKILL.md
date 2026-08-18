---
name: systematic-debug
description: 系统诊断构建、测试、运行、环境、权限或 Harness 工具失败。Dev、CR、TE 遇到稳定失败、间歇错误、504、Hook 异常或用户提供环境修复方法时使用；要求保留复现、假设、实验和可复用经验。
---

# Systematic Debug

## Inputs

- 原始失败命令、工作目录、退出码、完整错误和发生频率。
- 当前 diff、基线结果、相关需求/设计及用户提供的环境事实。
- 平台任务终态；504、超时或断流本身不等于 Worker 已失败。

## Procedure

1. 固定最小复现命令、输入、环境和预期结果；不能复现时记录触发条件与频率。
2. 保存首次失败证据，不先改代码掩盖现场。
3. 将问题归类为 `implementation`、`specification`、`environment`、`permission`、`tooling` 或 `intermittent`。
4. 列出可证伪假设，按证据强度排序；每轮只验证一个假设。
5. 先做只读诊断，再实施最小修复；不要顺手重构或扩大 Scope。
6. 修复后重跑最小复现，再运行受影响回归和 `post-verify`。
7. 记录每轮 `Hypothesis | Experiment | Observation | Decision`，包括用户给出的有效解决办法。
8. 若经验不能从代码、正式规格或 Git 直接推导，写入当前角色报告的 Memory Draft；不得只留在聊天中。

## Branches

- 实现缺陷：Owner=Developer；修复后重新 CR → TE。
- 规格或设计缺陷：Owner=Business Analyst/Solution Architect；当前角色不代改上游文档。
- 环境缺陷：写明已验证的修复步骤、适用条件和风险，再由原角色重跑验证。
- 权限缺陷：区分真实系统权限与 Hook 运输故障；不得绕过安全权限。
- Harness 工具缺陷：用等价底层命令继续业务验证，同时记录本体问题。
- 间歇失败：至少记录重复次数和共同条件；不得用一次偶然 PASS 关闭。
- 同一问题连续三轮仍无进展：停止堆补丁，报告已排除项、剩余假设和需要的外部决定。

## Output Contract

输出必须包含：症状、最小复现、分类、根因或剩余假设、实验记录、修复、复验、Owner、下一步和 Memory Draft。

只有最小复现与相关回归都通过，才可返回原流程；否则保留明确 FAIL/BLOCK，不能以“应该好了”结束。
