# Reporting Rules

本规则只在 Worker 写交付文档和 PM 校验 handoff 时加载。

## Document Schema

- 新文档必须从当前阶段模板生成并保留 `<!-- harness-document: <name>@3 -->`。
- 不删除模板要求的一级结构；不适用内容写 N/A 和理由，不能直接删节导致下游解析漂移。
- 删除示例行和 `<placeholder>` 后才能 PASS。
- 稳定 ID 不因措辞调整重排：REQ/Scenario、DES、TASK、Finding、Check、Test ID 各自保持唯一。

## Incremental Changes

- proposal 使用 Spec Delta；requirements 使用 Requirement Delta；design/tasks 使用 Design/Task Delta。
- revise 先读旧文档再局部修订，保留未被明确改变的内容和 ID。
- checklist 事实只在有证据时 carried_forward；旧审批、旧 RR/CR/TE PASS 永不继承。

## Checklist Results

- CR 必须逐项记录 `CHK-CR-001..008`；TE 必须逐项记录 `CHK-TE-001..008`。
- 每项写 Result、Evidence、Finding/Failure ID 和 N/A 理由。适用的 P0/P1 未检查不得 PASS。
- tasks 是跨角色活清单：SA 定义；Dev/CR/TE 只更新自己拥有的状态/证据列。

## Evidence

- 声称完成必须给出文件/diff/命令/退出码/日志/测试资产。
- 启动、冒烟、数据库验证不能由 compile/build/test 冒充。
- 机器证据必须与当前 diff 同轮；旧报告只作历史审计。

## Findings

每个阻断 finding 包含稳定 ID、严重度、Owner、精确位置、事实证据和 Required Fix。没有问题时明确写“无”，不能保留示例行。

## Conclusion

- BA/SA/RR/Dev：PASS 或 BLOCK。
- CR：PASS 或 REJECT。
- TE：PASS、FAIL 或 BLOCK。
- 文末只保留一个 `## Conclusion` 和一个允许值。

## Return Packet

Worker 最终返回必须包含：role、task_name、artifacts_updated、conclusion、summary、evidence、issues、next_owner。return packet 是 PM 路由摘要，不替代 owned 文档。

## Memory Draft

只有验证过且可能复发的工程经验才写症状、根因、修复、防复发/检测。一次通过且无复用价值写“无”；草稿缺失不阻断阶段或归档。
