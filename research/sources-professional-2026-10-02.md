# Professional workflow discovery — 2026-10-02

Research complements the initial [source ledger](sources-2026-10-02.md). Search terms: meeting notes action items agent skill; Claude meeting skills; experiment report SKILL.md; documentation sync Agent Skill; bilingual editing Agent Skill; Claude release skills.

## Primary pages actually fetched

| Workflow | Source | Useful observed scope and our independent design |
| --- | --- | --- |
| Meeting actions | https://academy.claude.com/use-cases/meeting-notes-and-filed-tasks-from-a-call-transcript | A first-party meeting workflow distinguishes notes/actions and can file tasks. Our local skill produces traceable action files and leaves external ticket creation outside the default scope. |
| Meeting actions | https://github.com/BuilderIO/agent-native/blob/main/templates/clips/.agents/skills/meetings/SKILL.md | A concrete transcript/meeting workflow with action items. Our helper verifies literal evidence and line bounds; no dependency on that application's meeting store. |
| Experiment report | https://github.com/lyf94697-droid/experiment-report-skill/blob/main/SKILL.md | Adjacent report-writing workflow, focused on lab/course artifacts and document templates. Our lightweight skill starts with existing numeric runs, explicit coverage/units/protocols and an original summarizer. |
| Docs and release | https://github.com/SteveVitali/agent-skills | Engineering workflows include documentation alongside code changes. Our separate local manifest and release preparation helpers keep evidence tied to explicit commits/artifacts. |
| Skill publication | https://cli.github.com/manual/gh_skill_publish | Native GitHub CLI skill validation and publication exist. Current installed CLI help confirms the command; use its dry-run as an additional standards check, not as evidence of publication. |

These are design/discovery references. No upstream skill bodies/scripts are copied and no upstream affiliation is claimed. Repository snapshots below are dated popularity proxies, not workflow demand/quality evidence.

## GitHub API snapshots

- BuilderIO/agent-native: 7029 stars; pushed 2026-10-02T11:01:42Z; https://github.com/BuilderIO/agent-native
- lyf94697-droid/experiment-report-skill: 7 stars; pushed 2026-07-25T06:16:40Z; https://github.com/lyf94697-droid/experiment-report-skill
- SteveVitali/agent-skills: 13 stars; pushed 2026-10-01T23:13:02Z; https://github.com/SteveVitali/agent-skills

## X discovery and access limits

- https://x.com/0xfene/status/2042047157767926056 — search-indexed 2026-04-08 first-person example of building reusable work routines, including meeting preparation and writing. Direct fetch failed on 2026-10-02. Historical indexed example only; timing/productivity claims are the author's report, not our measured benefit.
- https://x.com/Suryanshti777/status/2043925624356778062 — search-indexed 2026-04-14 resource roundup pointing to official catalogs/docs. Direct fetch failed. Useful catalog-discovery lead, not technical authority or evidence of today's most popular workflow.

No X posts were sent. No claim of a live trending feed or fresh audience/view metrics. Current product behavior is grounded in primary documentation and local CLI behavior.

## Selection rationale

The user explicitly requested daily and professional skills. Meeting actions, numerical experiment reports, changed-code documentation, release preparation and English/Chinese editing each yield a distinct artifact and need different evidence. Implement them as narrow skills with concrete scripts rather than a single large assistant or another prompt dump. Keep output structure and source provenance clear; test script failures separately from agent-produced prose.

Git command behavior source actually fetched: https://git-scm.com/docs/git — --no-lazy-fetch prevents on-demand promisor-object fetch; --no-optional-locks avoids optional locking. Local Git2.53.0 accepted the capability flag. The docs helper requires that capability and reports unsupported Git, rather than silently performing remote work.
