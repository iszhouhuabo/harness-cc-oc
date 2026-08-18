# Workflow Discipline

本规则只在发生流程或角色边界争议时加载。

## Always

1. PM 只调度；六个专业角色必须由平台 Agent/Task 工具真实启动。
2. 下游不能代改上游产物；发现问题必须写 finding、Owner 和 return packet。
3. propose 与 apply 后各有一个人工卡点；命令调用本身就是进入该阶段的授权。
4. 任务文档按阶段创建；文件存在表示已经进入过该阶段，不提前铺空模板。
5. Hook 是旁路验证，不是 Agent 权限系统；缺失时一次等价 fallback，不能循环重试。

## Profile

- quick：边界清楚的小改，BA → SA 自评。
- standard：默认，BA → SA → RR。
- refactor：跨域或结构迁移，增加 impact-analysis。

profile 是 PM 内部判断。不要让用户选择，也不要因相似包询问新建/扩展。

## 推进与回退

- 正常 PASS 后自动进入唯一后继，不请求用户确认内部步骤。
- RR BLOCK 回 BA/SA；修改后重新 RR。
- CR REJECT 回 finding Owner；修复后重新 CR。
- TE 的实现 FAIL 回 Dev，然后重走 CR/TE；需求偏差重新 propose。
- Task 暂时不可见时优先查询/等待/恢复同一 Task；平台确认终止前禁止再派相同角色。
- 同一问题三次未解决就停下，记录证据并升级真实决策，不继续堆补丁。

## 修订与失效

重新 propose 后，旧 SA/RR/Dev/CR/TE 阶段结论失效，必须重新走链路。旧文档保留审计价值，但只有本轮更新且晚于上游输入的报告可用于 PASS。

旧 checklist 不做无差别清空：

- 受影响、证据不足、误判完成：reset。
- 明确无影响且有可追溯证据：carried_forward。
- 被本轮明确废弃：deprecated。

carried_forward 只保留实现事实，不保留阶段批准；Dev/CR/TE 仍须本轮复核。

## 错误分层

- FAIL/BLOCK/REJECT：真实产物、实现、验证、权限或业务问题。
- WARN：可选治理、memory 草稿、非关键元数据缺失。
- DEGRADED：Hook/平台证据缺失，但可以执行等价检查。

脚本异常不等于业务失败。不要为了消除 Hook 错误让 Worker 重写已经成功落盘的文件。

## 规则增长

只有真实问题重复发生、可被机器稳定检测且收益高于误报成本时，才新增硬检查。第一次问题先写经验或 Skill；不为假设风险堆 checklist。
