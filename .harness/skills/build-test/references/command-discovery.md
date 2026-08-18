# Command Discovery Reference

仅在仓库同时存在多个构建体系、命令入口不明确或需要跨平台选择时读取。

## Discovery Order

1. 版本锁定：`.tool-versions`、`.java-version`、`.nvmrc`、`global.json`、`rust-toolchain*`、`go.mod`、Python 项目配置。
2. 仓库入口：`package.json` scripts、Gradle/Maven wrapper、Makefile/Taskfile、tox/nox、Cargo、Go packages。
3. CI 工作流：确认团队真实使用的构建、测试和环境变量入口。
4. 项目文档：只把命令当候选，仍需核对配置文件是否存在。
5. PATH 工具：仅在仓库没有 pin/wrapper 时使用，并记录实际版本。

## Common Candidates

| Stack | Version | Compile / Static | Unit / Integration | Build / Run |
| --- | --- | --- | --- | --- |
| Node | `node --version`; package manager version | 按契约选择 lint/typecheck | 合并目标的一次 package test/runner | 仅显式生产 bundle/产物 gate 才 build；不运行 dev/watch |
| Java | `java -version` 与 wrapper/toolchain 配置 | 开发期定向测试 | 默认 `./mvnw test` 或 `./gradlew test` | 仅契约要求制品/集成阶段时使用 package/verify/build 与有限 smoke |
| Python | `python --version`; pyproject/tox/nox | 仅契约要求时使用 ruff/mypy | pytest、unittest、tox、nox 或项目脚本四选一实际入口 | 不默认全量、多解释器、coverage、重建环境或 collect-only |
| Go | `go version`; `go env` | `go vet ./...`（若适用） | `go test ./...` 或受影响包 | `go build ./...` |
| Rust | toolchain 文件 | `cargo check`; clippy（若配置） | `cargo test` | `cargo build` |
| .NET | `global.json`; `dotnet --info` | `dotnet build` | `dotnet test` | `dotnet publish/run` |
| Ruby / PHP | 锁文件与项目 wrapper | 项目声明的 lint/static task | Bundler/Rake、PHPUnit 或 Composer script | 项目声明的 build/run |

不要机械执行表中所有命令。必须以仓库实际配置、受影响模块和 SA Verification Plan 为准；不存在的工具不得凭空引入。Java 使用满足当前任务的最低必要生命周期：无制品/打包/集成阶段要求时只运行 test，不先运行 compile；只有 Verification Plan 明确要求时才升级 package/verify/build，且不再执行被覆盖阶段。Maven `-pl` 不得默认添加 `-am`：目标模块独立变化且上游 artifact 一致性可证明时使用 `scoped_without_am`，上游/POM/SNAPSHOT/跨模块风险存在时使用 `also_make`。Vue/Node 的 test 与 build 通常是不同 gate，可各执行一次。

Vue/Node/Python 使用 `execution_scope=targeted_runner|expanded_gate`。targeted_runner 只执行受影响目标和 C 类 1–2 个相关回归；expanded_gate 仅在 Verification Plan 明确要求生产 build、全量、兼容矩阵、coverage 或额外静态 gate 时使用并记录原因。不得同时运行覆盖相同集合的 package scripts，不得先跑 pytest/unittest 再跑覆盖它们的 tox/nox。

## Cross-platform Rules

- 优先 wrapper 和 argv，不把 `&&`、管道或 shell alias 写成可移植契约。
- Windows 下 `mvnw`/`gradlew`、Node package manager、Bundler、Composer 等可能实际是同目录 `.cmd`/`.bat`；Worker 应使用项目 wrapper，只有人工 `delivery --replay` 才会保留原目录解析并通过 `ComSpec` 启动。Go、Rust、.NET、CMake/Ninja 等直接可执行文件仍按 argv 原样运行。
- PowerShell 与 shell 脚本必须在 Worker 报告中显式写成 `pwsh -File ...` / `powershell -File ...` 或 `bash ...`；Harness 不猜解释器、不绕过 execution policy，也不把缺少 Bash/PowerShell 误写成代码失败。
- Windows 使用仓库包装器并直接选择 `py -3`；macOS/Linux 使用项目 wrapper 并直接选择 `python3`。宿主系统已知时一次确定，不让用户轮流试探解释器命令。
- 路径包含空格时由执行工具传递参数，不在报告中制造无法复现的拼接字符串。
- 需要网络、容器、数据库或管理员权限时先记录依赖；不要把权限失败误判为代码失败。
- Vue/Vite、Node、Python、Java、Go、Rust、.NET、Ruby、PHP 的 dev/start/serve/watch/run 等可能常驻；验证表只记录能自行停止的 smoke 脚本。正常 delivery 只审计且不执行，人工重放也拒绝常驻服务命令。
