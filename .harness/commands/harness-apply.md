# Harness Apply

用户调用本命令就是 apply 审批，不得再次询问是否执行；本命令不自动归档。

Dev → CR → TE 以及 CR/TE 打回后的返工链全部自动推进。用户在失败或返工后说“继续”，表示立即恢复当前链路，不是新增审批点；除真实业务取舍、权限、安全或不可恢复环境问题外，禁止询问“要我现在执行吗”。

## Entry And Handoff

1. 读取 board、任务包和用户 re-run 反馈。
2. 执行 readiness-for-apply；OpenCode 调用 `harness_change(action=readiness, forApply=true, ...)`，其他平台运行等价脚本。它要求本轮 propose 已完成，或任务从 `AWAITING_ARCHIVE` 重跑 apply。
3. OpenCode PM 调用 `harness_change(action=board, status=APPLY, boardStage=development, ...)`，其他平台执行等价 board 更新。需求/方案偏差必须退出 apply，交用户重跑 propose。
4. 每个 handoff 包含 `TASK_NAME=<change-id>`、`TASK_ROOT=harness/specs/<change-id>`、本轮目标、`TASK_ROOT` 下的精确输入/owned outputs、实际 diff/用户反馈、禁止写入、完成条件和固定 Return Contract；`.harness/` 只用于本体契约、模板、Skills、规则和脚本，绝不是任务包目录。
5. Worker 返回后 PM 读取文件和 return packet，不以聊天自述替代产物。PASS 或返工完成且无人工卡点时立即启动唯一后继。
6. `git status/diff` 不是推进前置条件；OpenCode 需要取证时只调用 `harness_git_read`，相同 action 与参数最多执行一次。成功空输出、工具异常或重复调用保护都不得触发原样重试，优先依据 owned outputs、Return Contract 和阶段验证继续。
7. PM 不直接执行 `mvn/gradle/npm/pnpm/yarn/pytest` 等项目命令。正常 delivery 只审计 Worker 本轮报告的结论、结构、baseline、时序、命令安全、退出码和证据，返回 `mode=evidence_audit`、`checks=[]`，不重放项目命令；OpenCode Task-after 和 Claude Hook/fallback 都不得添加 `--replay`。`--replay` 仅用于人工诊断明确复现。禁止并发 Dev/TE delivery，也禁止用旧 TE 证据验证新 Dev 修复。
8. Dev/TE 先在报告 `Verification Inputs` 声明有界任务输入，再用可重复的 `--input <path>` 调用 `harness.py evidence-ledger` 查询同角色、同输入指纹、同 cwd/argv 记录；`REUSABLE` 复用证据，`MISS/STALE` 才执行并在成功后立即 `--record`。范围外用户并行改动只告警，范围内源码/配置/测试资产变化使证据失效；账本不跨角色复用，不能用 Dev 结果替代 TE。
9. owned 产物缺失、schema/必需章节/唯一 `## Conclusion` 不合规或 delivery FAIL 都是真实阶段失败，必须退回 Owner；禁止以“实质内容看起来已完成”降级放行。
10. 机械格式由 `harness.py preflight` 在 Worker 停止前检查。Claude 失败时当前 Worker 原地修正，不新建同角色 Task；TE-owned 报告格式修订不重走 Dev/CR，且验证输入未变时可引用 TE 自己的可复用证据。

## Developer

1. 执行 stage 动作 `development`；OpenCode 调用 `harness_change(action=stage, stage=development, ...)`。
2. 加载 Developer 契约、dev-log 模板、build-test/systematic-debug/post-verify Skills。
3. 启动 `developer`。Dev 按 TASK/REQ/DES 做有界实现，更新 Dev checklist，执行 runtime、build/test、startup/smoke/database 等适用 gate。
4. Dev PASS 后，OpenCode 调用一次 `harness_change(action=delivery, role=developer, ...)`；Claude Code 读取同步 Hook result，缺失时才补跑一次。该步骤只审计 Dev 已执行证据，不再次构建或测试；Dev delivery 期间不得启动 TE delivery。
5. 文档与机器证据 PASS 后立即进入 CR。

## Code Review

1. 执行 stage 动作 `review`；OpenCode 调用 `harness_change(action=stage, stage=review, ...)`。
2. 加载 CR 契约、code-review 模板、`CHK-CR-001..008` checklist 和 code-review Skill，启动 `code-reviewer`。
3. CR 必须逐项填写 Checklist Results，只审不改。Dev-owned REJECT 回 Dev；Dev 修复 PASS 后 PM 立即重新启动 CR，不征求确认。TE-owned 交 TE；Upstream-contract 退出 apply。
4. CR PASS 后立即进入 TE。

## Test Engineering

1. 执行 stage 动作 `testing`；OpenCode 调用 `harness_change(action=stage, stage=testing, ...)`。
2. 加载 TE 契约、test-report 模板、`CHK-TE-001..008` checklist、test-e2e/post-verify Skills，启动 `test-engineer`。
3. TE 按 A/B/C/D 测试分类覆盖本轮 GWT、受影响历史规格和工程回归；不修生产代码。
   - A/B/C/D 是覆盖分类，不是四条独立命令；每类必须 PASS/FAIL/N/A，同一结果可以映射多个 Class。
   - B 执行当前任务适用 GWT 的真实 API/CLI/任务/数据库/UI 链路；C 在 standard/refactor 选择 1–2 个最相关历史场景；D 由 TE 独立执行一次最低必要工程验证和适用 baseline/post-verify，不复用 Dev 结果。Maven `-pl` 不得默认添加 `-am`，必须先记录 scoped_without_am/also_make 的影响面证据。
   - Vue/Node/Python 必须记录 targeted_runner/expanded_gate；不默认 Node build、Python 全量/多解释器/tox-nox矩阵/coverage，同一 runner 覆盖集只执行一次。
   - 不默认全量测试或全量 E2E，不要求截图、不强制浏览器；相同 runner/目录/模块/profile 可安全合并的目标只启动一次进程。
4. Dev-owned FAIL 回 Dev 后自动重走 CR/TE；TE-owned 测试资产问题由 TE 修复重跑；上述阶段内返工均不征求确认。Upstream-contract 退出 apply；环境问题必须有证据。
5. TE PASS 后，OpenCode 调用一次 `harness_change(action=delivery, role=test-engineer, ...)`；Claude Code 读取同步 Hook result，缺失时才补跑一次。该步骤只审计 TE 独立执行的证据，不再次构建或测试；结果必须包含过滤控制面噪声后的 baseline compare，TE 早于最新 Dev/CR 时返回 stale 并重走 CR/TE。

## Close

先运行 `harness.py apply-close <change-id>`；OpenCode 在 `harness_change(action=board, status=AWAITING_ARCHIVE, ...)` 内强制执行同一门禁。门禁核对三个报告结构与唯一 PASS、Dev/TE delivery 的报告/baseline/Verification Inputs 指纹，以及 Dev → CR → TE 文件时序。验证范围外工作区变化只进入 warnings；范围内变化、报告变化或时序过期才失败。只有通过后才能更新 board 并等待 archive。

Task 504/超时时查询、等待或恢复同一 Task；平台确认旧 Task 失败/取消前禁止重复派发。同一问题三次未解决时停止堆补丁。
