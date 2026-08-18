---
name: build-test
description: 发现并执行项目真实的编译、静态检查、单元测试、集成测试、构建、启动和冒烟入口。SA 制定 Verification Plan、Dev 完成实现或 TE 复核构建链时使用；不得凭 PATH 猜版本或用聊天自述代替证据。
---

# Build And Test

## Inputs

- 当前任务的 `requirements.md`、`design.md`、`tasks.md`。
- 仓库实际 diff、构建配置、版本锁定文件和 CI 配置。
- SA 的 Verification Plan；若缺失关键 gate，先记录为设计缺口。
- 当前角色拥有的报告模板：Dev 使用 `dev-log.md`，TE 使用 `test-report.md`。

## Procedure

1. 定位受影响模块及其工作目录，不从仓库根目录盲跑所有命令。
2. 读取版本锁定和项目入口；需要选择不同技术栈命令时才读取 [command-discovery.md](references/command-discovery.md)。
3. 为每个适用逻辑 gate 建立执行表：runtime、dependency、typecheck/test、必要时的 artifact/integration、startup/smoke、database/migration。先识别生命周期覆盖关系，不把 Maven/Gradle 的 compile、test、package/build 拆成必跑命令清单。Maven `-pl` 命令还必须先选择 `reactor_scope=scoped_without_am|also_make`，不得默认添加 `-am`。
4. 每条命令使用明确工作目录和 argv 语义；不要依赖仅在当前交互 shell 中成立的 alias。
5. Windows 上 Node 包管理器常由 `npm.cmd`、`npx.cmd`、`pnpm.cmd`、`yarn.cmd` 或 `corepack.cmd` 提供；发现 `node --version` 成功而包管理器裸命令报 `WinError 2` 时，应按包装器解析，不得直接判定工具未安装，也不得要求用户修改 PATH。
6. Python 项目不强制 pytest。先从 `pyproject.toml`、测试源码、tox/nox 配置或 CI 确认真正 runner：pytest 项目记录项目解释器的 `python -m pytest`，标准库 unittest 项目使用 `python -m unittest`/`python -m unittest discover`，也可使用 tox、nox 或项目脚本。不要使用 `python -m test`（它是 CPython 自身测试入口），也不要记录依赖系统 PATH 的裸 `pytest`；旧报告的裸 pytest 仅在 executable 缺失时允许 delivery 使用项目 `.venv*`/`venv` 做等价重试。
7. 先把本轮源码、测试资产和构建配置写入报告 `Verification Inputs`，再执行运行时/依赖检查。每个昂贵命令启动前调用 evidence ledger；Windows 使用 `py -3 .harness/scripts/harness.py evidence-ledger <task> --role <developer|test-engineer> --cwd <dir> --input <path> --command "<单一 argv>"`，macOS/Linux 使用 `python3 .harness/scripts/harness.py evidence-ledger <task> --role <developer|test-engineer> --cwd <dir> --input <path> --command "<单一 argv>"`；多个有界输入重复传 `--input`。`REUSABLE` 时引用账本证据而不重跑，`MISS/STALE` 才执行，并在退出码 0 后立即追加 `--record --exit-code 0 --evidence "<实际证据>"`。范围外用户并行改动不使证据失效；范围内输入变化必须重验。账本按角色隔离，TE 不得复用 Dev 条目。随后只运行开发中需要的定向测试，收工时再执行一次覆盖当前任务的非重叠验证。
   - Java 选择满足需求的最低必要生命周期。没有制品、打包或集成阶段要求时，Maven 使用一次 `./mvnw test`，Gradle 使用一次 `./gradlew test`；`test` 已覆盖 compile，禁止在代码、模块、profile 和参数未变化时先执行 compile 再执行 test。
   - Maven 只修改目标模块、父 POM/公共配置和上游 reactor 模块均未变化，且依赖 artifact 与当前代码一致性可证明时，使用 `scoped_without_am`：`./mvnw -pl <module> test`。上游源码/POM变化、同版本 SNAPSHOT 一致性不明、公共插件/配置变化或跨模块行为存在时，使用 `also_make` 并保留 `-am`。不能证明安全时不得猜测省略。
   - 只有 requirements/design 的 Verification Plan 明确要求制品、package 阶段或 verify/build 专属集成 gate 时，才升级到 `package`、`verify` 或 `build`；升级后不得再记录其已覆盖的 compile/test。不同模块、profile 或无法覆盖的独立 gate 才拆分，并记录原因。
   - 开发过程中可运行定向测试；最终报告只保留本轮最后一次非重叠验证命令。上下文压缩、Worker 重入、CR 或 delivery 都不是重新执行命令的理由；只有证据之后代码、配置、依赖、测试资产或执行参数发生相关变化，证据才失效。
   - Vue/Node 的 test 与 build 通常是不同 gate，可以各执行一次；不要因 Java 生命周期规则错误合并。Python 的 pytest/unittest/tox/nox 及其他语言 gate 同样由当前 Worker 实际执行一次，不能依赖 delivery 代跑。
   - Vue/Node 与 Python 先记录 `execution_scope=targeted_runner|expanded_gate`。Vue/Node 只有 Verification Plan 明确要求生产 bundle、类型/构建配置或产物验证时才执行 build；同一 Vitest/Jest/Playwright/ESLint runner 的目标合并为一次，不重复执行覆盖集相同的 package scripts，不运行 watch/dev。Python 只选择仓库实际入口 pytest、unittest、tox、nox 或项目脚本之一；tox/nox 已覆盖同一测试时不先跑 pytest/unittest，不默认全量、多解释器矩阵、coverage、依赖重装或 collect-only。
8. 涉及可运行服务、页面或任务时，启动后执行健康检查或关键冒烟，并可靠停止临时进程；报告只记录可在超时内自行退出的 smoke 脚本，不直接记录 `npm run dev`、`java -jar`、`spring-boot:run` 等常驻命令。
9. 保存命令、工作目录、退出码和关键输出；不要只写“已验证”。
10. 运行 baseline compare：Windows 使用 `py -3 .harness/scripts/harness.py baseline <task> compare`；macOS/Linux 使用 `python3 .harness/scripts/harness.py baseline <task> compare`，记录修改前后差异。
11. 将结果写入角色报告的规范证据区（Dev 为 `Verification Results`，TE 为 `Test Matrix`）并给出唯一结论；每条 PASS 必须有 Exit Code=0 和非空、非占位 Evidence。每行 Command 是单一 argv，不写 `cd`、`&&`、管道、重定向或说明文字。明确多目标可使用 runner 原生语法；这些命令只在人工 `delivery --replay` 时参与安全合并，正常 delivery 只审计且不执行。

## Decision Rules

- `PASS`：所有适用 gate 返回成功，证据可复现，且没有新增未解释失败。
- `FAIL`：任一必需 gate 失败、命令无法复现、工作目录错误或证据与当前 diff 不同轮。
- `N/A`：仅限确实不适用；必须写明需求、设计或模块事实依据，不能用环境问题冒充 N/A。
- 不以是否安装 pytest 判断 Python 项目能否验证；只要求项目实际声明的 runner 可执行并覆盖约定 gate。
- 环境或命令失败时，加载 `systematic-debug`，不要重复运行同一命令碰运气。
- Verification Plan 遗漏关键 gate 时，不得自行悄悄缩减范围；Dev 报告风险，TE/CR 按 Owner 路由给 SA。

## Output Contract

每条验证至少记录：`Gate | Working Directory | Command | Exit Code | Result | Evidence`。

收工前确认：

- 每个受影响模块都有适用 gate 或有证据的 N/A。
- `Verification Inputs` 已覆盖会影响本轮命令结果的源码、配置和测试资产；TE 范围覆盖 Dev Changed Files。
- 每条 PASS 都有真实命令和退出码。
- 最终证据只使用满足当前任务的最低必要 Java 生命周期；没有 compile→test 或 test→package/verify/build 的重复链，必须升级或拆分时已引用 Verification Plan 并记录原因。
- Maven `-pl` 已记录 `reactor_scope`、上游/父 POM/SNAPSHOT/跨模块检查证据；`scoped_without_am` 只有在一致性可证明时使用，TE 必须独立执行而不是复用 Dev 结果。
- Vue/Node/Python 已记录 `execution_scope`、选用 runner、目标集合和 expanded_gate 原因；同一覆盖集没有被 package script、tox/nox 或多个 runner 重复执行。
- 临时服务、容器和测试数据已清理或明确保留原因。
- `.harness/`、`.opencode/`、`.agents/` 属于控制面，不计入业务 baseline 的 introduced/resolved/current changed paths；其完整性由 framework 自检负责。
- 失败包含 Owner、最小复现和下一步，不把失败埋在日志中。
