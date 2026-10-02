# Next selected workflow: meeting notes to actions

Based on the initial skill-research forward evaluation, this workflow has a clear everyday use with less overlap and lower maintenance than another broad report writer or documentation framework.

Input: one user-selected notes/transcript text plus optional meeting date/timezone and participant mapping.

Outputs: decisions.md, actions.json and unresolved.md. Action records distinguish task, owner/status of owner evidence, deadline/status of deadline evidence, source location and blocked dependencies. Missing owner/deadline stays unresolved; a question is not a decision. Relative deadlines require the actual meeting date and timezone before conversion.

Acceptance: preserve quoted source meaning; separate discussion/proposals/decisions; validate structured actions; retain contradictory ownership or date evidence for review; test a complete meeting plus notes with ambiguous deadlines and unavailable participants. No email/calendar/task-system writes unless separately requested.

Delivery: portable SKILL.md, self-contained validator, synthetic examples, isolated forward test, multi-platform CI, changelog and v0.2.0 release.
