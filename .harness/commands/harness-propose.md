# Harness Propose

只完成影响分析、需求、方案和就绪评审；禁止修改业务源码、测试、依赖和构建配置。

## Entry

1. 从用户输入取得或拟定 ASCII change-id；相似任务只作上下文，不询问新建/扩展。
2. PM 自动选择 profile：小且边界确定用 quick，跨规格域/结构迁移用 refactor，其余 standard；不让用户配置 profile。
3. 执行 init 动作：OpenCode 调用 `harness_change(action=init, task=<change-id>, description=<中文需求摘要>, profile=<profile>)`；其他平台运行等价 `harness.py init`。它创建/保留 proposal 并刷新本轮 `baseline.json`；已有包进入 revise，board 重开为 PROPOSE，旧下游 PASS 失效。
4. 读取 archive/memory/spec index，只打开命中的正文。

## Handoff Contract

每次真实 Agent/Task handoff 必须写明：

- `TASK_NAME=<change-id>`、`TASK_ROOT=harness/specs/<change-id>`、profile、`change_mode=new|revise`。
- 当前 `work_mode`/目标、精确 required inputs、owned output paths。
- Scope/Non-goals、禁止写入、完成条件和允许结论。
- 返工 finding/用户反馈，以及“必须实际更新 owned 文件并返回角色契约中的 Return Contract”。

所有任务包输入和 owned outputs 必须写成 `TASK_ROOT` 下的明确路径；`.harness/` 只用于角色契约、模板、Skills、规则和脚本，禁止把任务包解析到 `.harness/` 或 `.harness/specs/`。

Worker 返回后 PM 直接读取 owned 文件和 return packet；缺文件、未更新、占位符残留、结论不合法或字段缺失都按该 Owner 的 BLOCK 处理，PM 不代修。正常 PASS 自动进入唯一后继。
在 Claude 中，机械格式问题由 `SubagentStop` preflight 阻止当前 Worker 退出并原地修正；PM 不得因同一问题再启动一个 Worker。其他平台收到 preflight 失败时也只路由当前 Owner，不波及无关上下游。

## Refactor Impact Analysis

refactor 在 BA 前执行：

1. 执行 stage 动作 `impact-analysis`；OpenCode 调用 `harness_change(action=stage, stage=impact-analysis, ...)`。
2. 加载 SA 契约和 impact-analysis 模板，以 `work_mode=impact_analysis` 启动 `solution-architect`。
3. PASS 后进入 BA；BLOCK 的拆分、范围或外部决定交 PM/user。这个 SA Task 结束后才开始 BA，不能与后续 design Task 混为一个存活 Worker。

## BA Requirements

1. 执行 stage 动作 `requirements`；OpenCode 调用 `harness_change(action=stage, stage=requirements, ...)`。
2. 加载 BA 契约、proposal/requirements 模板；refactor 额外把 impact-analysis 交给 BA。
3. 启动 `business-analyst`。BA 必须更新 Proposal/Requirement Delta、稳定 REQ/Scenario、非目标和阻塞问题。
4. BLOCK 只有真实业务取舍才询问用户；用户回答后重新派 BA。PASS 立即进入 design。

## SA Design

1. 执行 stage 动作 `design`；OpenCode 调用 `harness_change(action=stage, stage=design, ...)`。
2. 加载 SA 契约、design/tasks 模板和 build-test Skill，以 `work_mode=design` 启动 `solution-architect`。
3. revise 必须逐项将旧任务标为 reset/carried_forward/deprecated/new，并给依据；不得清空全部已完成事实，也不得沿用旧阶段 PASS。
4. quick 要在 design 完成完整 Readiness Self-Check；standard/refactor PASS 后立即进入 RR。

## RR

1. 执行 stage 动作 `readiness`；OpenCode 调用 `harness_change(action=stage, stage=readiness, ...)`。
2. 加载 RR 契约和 readiness 模板，启动 `readiness-reviewer`。
3. RR 必须逐项记录 schema、增量稳定性、追踪、任务可执行性和验证契约；不得修改 BA/SA 文件。
4. BLOCK 按 finding Owner 回最上游 BA/SA；修订完成后重新启动 RR，PM 确认不能替代复评。

## Close

执行 readiness 验证；OpenCode 调用 `harness_change(action=readiness, ...)`。通过后再调用 `harness_change(action=board, status=AWAITING_APPLY, boardStage=readiness, ...)`；其他平台执行等价脚本和 board 更新。随后汇报增量范围、追踪、风险、开放项和产物路径，等待用户批准 apply。

Task 504/超时时查询、等待或恢复同一 Task；平台确认终止前禁止再启动同角色 Worker。同一问题三次未解决才升级真实决策。
