# Harness Archive

用户调用本命令就是 archive 审批。不得再次询问确认。

## 前置

- board 状态必须是 `AWAITING_ARCHIVE`。
- apply close gate 必须仍为 PASS；归档只做兜底复核，不应首次发现阶段产物问题。
- `dev-log.md`、`code-review.md`、`test-report.md` 的最新结论必须全部 PASS。
- 若发现规格与实现不一致，停止归档并按 Owner 回退。

## 执行

1. 将本次已验证的 Spec Delta 合并到项目长期需求文档；不要把未验证猜测写入长期规格。OpenCode PM 只通过 `harness_pm_write` 写入允许的长期文档路径，不能编辑任务包或业务代码。
2. 对 RR/Dev/CR/TE 的 `Reusable Experience Draft`、任务内 memory 草稿和遗留的 `harness/memory/<task>.md` 执行 memory README 五项准入。没有非空草稿可直接归档并接受 warning；出现非空草稿后不得跳过处置。
3. 处置只能选择一种：不合格则 `rejected` 并写明确原因；与既有条目重复则 `duplicate`，指向已进入中文 index 的 entry 并说明原因；合格则先通过 `harness_pm_write` 创建/更新完整 `harness/memory/entries/*.md` 和 `index.md`，再标记 `accepted`。禁止把任务总结包装成记忆。
4. OpenCode 调用 `harness_change(action=memory-disposition, task=<change-id>, memoryStatus=<accepted|rejected|duplicate>, ...)`；其他平台运行等价 `harness.py memory-disposition`。只有返回 `verdict=PASS` 才继续；草稿内容之后变化必须重新处置。
5. OpenCode 调用 `harness_change(action=archive, task=<change-id>)`；其他平台运行等价 `harness.py archive`。
6. 只接受脚本 JSON 中 `ok: true`，且 `postconditions.source_absent/archive_present/index_updated/board_done` 全部为 `true`。任一为 `false` 时报告对应项并停止；同时核对返回的 `memory_disposition.status` 与本次处置一致。

禁止额外运行 `Test-Path`、`test -d/-e/-f`、`Get-ChildItem`、`ls` 等平台 Shell 命令确认归档；路径和元数据后置条件统一由 Python 脚本跨平台检查。归档不补做 Worker 产物，不修改业务代码。脚本已确认成功后直接报告完成。
