# Worked prompts

## Materials intake

“用 $workflow-materials-intake 盘点我指定的材料目录。列出重复文件，区分候选版本，保留原文件，生成可以直接查阅的索引。”

Expected: inventory.json, inventory.md, material-index.md, duplicate evidence and unresolved version status.

## Desktop triage

“用 $workflow-desktop-triage 给这个 Downloads 目录做分类副本，放入指定的新目录。不要删除原文件，保留同名子目录文件，告诉我哪些需要人工复核。”

Expected: classification plan, copies, copy-ledger.json and an accurate report distinguishing copied from moved files.

## Source-backed writing

“用 $workflow-source-writing 根据这些日志和资料写一份 200 字技术项目说明。保留实验口径，来源不完整的说法不要写成已确认结果。”

Expected: complete draft, evidence-ledger.json and material unresolved claims.

## Repository handoff

“用 $workflow-repo-handoff 核对这个仓库实际分支与代码，运行适当验证，写一份下一位开发者能接着工作的交接说明。不要推送或丢弃改动。”

Expected: git-snapshot.json, exact commands/results and handoff.md with a next action.

## Skill research

“用 $workflow-skill-research 搜索 GitHub 和 X，比较三个适合我日常工作的技能选题。记录来源日期和访问情况，选一个小而实用的，给出明确验收标准。”

Expected: dated source ledger, candidates.json, ranked.json and one implementable acceptance specification.

## Meeting actions

“用 $workflow-meeting-actions 把这份会议记录变成行动清单。只保留有证据的负责人和日期，未明确的留待确认，不创建外部任务。”

Expected: actions.md, actions.json, review.md and source-quote/line validation.

## Experiment reporting

“用 $workflow-experiment-report 根据这份已有结果写实验报告。预期样本数和评测协议如附件说明，明确有效返回覆盖率及指标分母，不补造结果。”

Expected: summary.json and complete report with coverage, protocol, units, returned-only statistics and precise/approximate numeric evidence.

## Documentation sync

“用 $workflow-docs-sync 根据这两个提交更新受影响的 README 和使用文档。保留代码与已有未提交编辑，运行必要的文档示例并记录验证结果。”

Expected: explicit commit-change manifest, affected-doc plan, actual authorized edits and verification report.

## Release preparation

“用 $workflow-release-prep 为这个小项目准备指定版本的发布资料。核对版本、变更说明、这些构建产物和校验和，区分已准备与已验证；暂不发布。”

Expected: local readiness evidence, release-notes.md, release-checklist.md and SHA256SUMS; unrun build/tests/CI remain unverified.

## Bilingual editing

“用 $workflow-bilingual-edit 把这份中文技术介绍润色为专业英文，保留数字、单位、日期、项目名和成果状态，附事实保留映射。”

Expected: complete edited prose, preservation-map.json and concise editing notes, with literal checks plus semantic review.
