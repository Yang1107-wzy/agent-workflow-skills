# 实用 Agent 工作流 · Codex / Claude Code Skills

[English](README.md) · [示例提示词](examples/prompts.md) · [选题来源](research/sources-2026-10-02.md) · [长期路线图](ROADMAP.md)

把经常重复的材料处理、文件整理、专业写作、编程交接和技能调研变成可复用工作流。首版包含五个独立技能、可执行 Python 脚本、安装器和验证示例，不需要付费 API 或后台服务。

| Skill | 用途 | 交付物 |
| --- | --- | --- |
| `workflow-materials-intake` | 材料盘点、资料分类、重复与版本核对 | SHA256 清单、重复证据、语义材料索引 |
| `workflow-desktop-triage` | 桌面、下载目录、散乱文件整理 | 分类预览、校验过的分类副本、路径台账 |
| `workflow-source-writing` | 基于资料的技术报告与专业写作 | 完整文稿、主张与来源台账、结构检查 |
| `workflow-repo-handoff` | 编程交接、恢复陌生分支、核对真实验证状态 | 当前 Git 快照、验证命令与结果、下一步 |
| `workflow-skill-research` | GitHub/X 技能选题、工作流库维护 | 有日期的来源清单、可解释排序、实现规格 |

## 安装

Python 3.10+，脚本无第三方运行时依赖；编程交接快照需要 Git。

```sh
git clone https://github.com/Yang1107-wzy/agent-workflow-skills.git
cd agent-workflow-skills
python scripts/validate_skills.py
python scripts/install.py --target both
python scripts/install.py --target both --apply
```

第一条安装命令预览，`--apply` 实际复制。已有技能目录会被拒绝，不覆盖。也可从 Release 下载 ZIP，解压后运行同样的命令。

- Codex 用户目录：`~/.agents/skills`；项目目录：`.agents/skills`。
- Claude Code 用户目录：`~/.claude/skills`；项目目录：`.claude/skills`。
- 只安装一个平台用 `--target codex` 或 `--target claude`；只装某项用 `--skill workflow-materials-intake`。
- 项目安装加 `--scope project --project-root 项目路径`。

目录依据 [Codex 官方文档](https://learn.chatgpt.com/docs/build-skills) 和 [Claude Code 官方文档](https://code.claude.com/docs/en/skills)。如未显示新技能，新开会话或重启客户端。安装器不改设置，不安装 Claude Code，也不上传技能到 Claude.ai/Cowork。

## 在 Agent 中使用

Codex 聊天：

```text
用 $workflow-materials-intake 整理这个材料目录，输出可查阅的资料索引。
用 $workflow-source-writing 根据这些证据写一份技术项目总结。
```

Claude Code 聊天：

```text
/workflow-desktop-triage 帮我分类这个下载目录，先保留原文件。
/workflow-repo-handoff 核对当前仓库，写一份可继续开发的交接说明，不推送代码。
```

Agent 也可根据普通自然语言请求匹配描述。脚本提供确定性辅助，语义分类、来源核对和写作由 Agent 完成；这不是独立聊天机器人。

## 直接体验脚本

```sh
python skills/workflow-materials-intake/scripts/inventory.py examples/materials
python skills/workflow-desktop-triage/scripts/triage.py examples/materials ../classified-demo
python skills/workflow-source-writing/scripts/check_ledger.py examples/evidence-ledger.json --format json
python skills/workflow-skill-research/scripts/rank_candidates.py examples/candidates.json
```

桌面脚本默认只预览；需要分类副本时加 `--apply`，输出目录必须是源目录之外的新目录。它校验副本字节，保留原文件，不会宣称桌面已清空。真正移动文件时，技能指导 Agent 按已授权范围使用文件工具，并记录路径台账。

盘点忽略隐藏项、符号链接、应用包、代码仓库和未完成下载；类别按扩展名建议，默认最多 1,000 个普通文件。报告应保存到扫描目录之外。名字含 final、修改时间较新或哈希重复，都不能单独证明批准或提交。

## 已做验证与边界

提供脚本测试、Linux/Windows/macOS CI、每项技能的独立合成任务验证，具体见 [EVALUATION.md](EVALUATION.md)。测试了重复文件、同名子目录、中文路径、旧编码终端、源文件保护、安装冲突、证据台账和实际 Git 状态。

来源台账检查器只校验结构与声明的证据，不替代事实核对。选题评分是公开的主观标准，不是客观热门榜。兼容格式与安装目录已验证；本轮没有实际运行 Claude Code 客户端，不保证不同模型产生完全相同的行为。

只公开合成示例和原创技能/代码。GitHub 和 X 的选题来源、日期与访问失败均记录在研究清单；没有复制其他仓库的整段技能内容。

## 后续方向

实验结果报告、会议纪要行动项、项目文档同步、小工具发布准备、双语专业编辑，将按路线图逐项实现、测试和发布。路线图本身不创建定时任务，本仓库未配置自动唤醒。

MIT 许可。开发验证：`python -m unittest discover -s tests -v` 和 `python scripts/validate_skills.py`。
