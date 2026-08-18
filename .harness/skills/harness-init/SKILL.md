# Harness Init

仅在项目首次接入或 Harness 升级后显式加载，不属于日常 propose/apply/archive。

```text
Windows:       py -3 .harness/scripts/harness_init.py
macOS/Linux:   python3 .harness/scripts/harness_init.py
```

可用 `--tool claude|opencode|trae|all` 和 `--dry-run`。

初始化器只生成项目级薄入口：

- Claude Code：六角色、三命令、五个 Skills；六角色 `SubagentStop` 先做 owned 产物机械预检，仅 Developer/TE 继续旁路 delivery 证据审计。
- OpenCode：一个与 Build/Plan 同级的 Harness PM、六个 SubAgent、三条绑定 PM 的命令、五个 Skills；单一 Task-after 插件失败时静默降级。PM 的 Task allowlist 只包含六个 Harness Worker，禁止 persona fallback。
- Trae：六角色和三命令；没有稳定角色收工事件，因此不安装文件写入 Hook，PM 在收工时补跑验证。

任何平台都不安装写入租约、启动证明或自建 Worker 生命周期状态机。现有用户自定义 Hook 会保留，只清理 Harness 旧适配项。
