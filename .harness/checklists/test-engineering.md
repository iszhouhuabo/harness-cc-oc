# Test Engineering Checklist（TE 固有检查清单）

TE 必须检查本清单中的适用项，并在 `test-report.md` 的 Checklist Results 表中逐项记录结果。清单定义检查规则；报告记录本次事实、证据和关联失败。

| 检查项ID | 名称 | 严重度 | 检查规则 | 失败时结论 | 适用范围 |
| --- | --- | --- | --- | --- | --- |
| CHK-TE-001 | 可复现验证证据检查 | P0 | TE PASS 必须包含可复现命令/步骤、退出码或观察结果和关键输出摘要；不要求截图，但声明的报告、日志或其他证据文件必须真实存在 | FAIL | 所有变更 |
| CHK-TE-002 | A/B/C/D 与验收场景覆盖检查 | P0 | 四类是覆盖分类而非四条独立命令，必须逐类 PASS/FAIL/N/A；每个适用 SHALL/GWT 必须映射到真实可执行测试/步骤和证据 | FAIL | 所有功能变更 |
| CHK-TE-003 | 最低必要工程验证检查 | P0 | 所有受影响模块必须有 TE 独立执行的适用工程验证，不得复用 Dev 结果；同一生命周期/runner 覆盖集不重复。Maven `-pl` 记录 scoped_without_am/also_make，不默认 `-am`；Vue/Node/Python 记录 targeted_runner/expanded_gate，不默认 build、全量、tox/nox矩阵或 coverage | FAIL | 所有代码变更 |
| CHK-TE-004 | 真实链路与环境检查 | P0 | 受影响 API、页面、任务、数据库或服务必须完成适用真实链路/启动/冒烟或有事实 N/A；UI 不强制浏览器，不要求截图 | FAIL | 涉及运行链路的变更 |
| CHK-TE-005 | 数据库与迁移检查 | P0 | 涉及数据库、迁移、初始化、默认数据或持久化路径时，必须验证初始化/迁移/连接 | FAIL | 数据相关变更 |
| CHK-TE-006 | 有界回归范围检查 | P1 | standard/refactor 的 C 类选择 1–2 个最相关历史场景，不默认全量；选择依据、未覆盖风险和人工全量入口必须记录 | FAIL | 标准或重构变更 |
| CHK-TE-007 | 环境归属检查 | P1 | 环境问题必须有证据支撑；不能用 Environment-owned 掩盖实现缺陷 | FAIL | 出现运行或验证失败时 |
| CHK-TE-008 | 角色边界检查 | P0 | TE 不得修改生产代码、Dev-owned 单元/组件测试、需求、方案或审查报告；可维护 TE-owned E2E/cases/验收脚本和证据资产 | FAIL | TE 阶段 |
