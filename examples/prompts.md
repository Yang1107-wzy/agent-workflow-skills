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
