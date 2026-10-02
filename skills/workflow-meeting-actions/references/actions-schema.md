# Action evidence contract

The helper requires Python 3.10 or newer, uses only the standard library and reads UTF-8 files. It prints to stdout; it never writes files. Preserve the transcript used for the locators. Text reading normalizes CRLF/CR newlines to LF; quote matching otherwise preserves exact spelling, spacing and punctuation.

```json
{
  "schema_version": 1,
  "meeting": {"date": null, "timezone": null},
  "actions": [
    {
      "id": "a1",
      "action": "Send the revised budget",
      "status": "committed",
      "owner": "Mira",
      "due_text": "by 2026-10-09",
      "due_date": "2026-10-09",
      "resolution_basis": null,
      "source": {
        "start_line": 2,
        "end_line": 2,
        "quote": "Mira: I will send the revised budget by 2026-10-09."
      }
    }
  ]
}
```

All shown fields are required. Extra fields are allowed. An empty `actions` array is valid when no concrete actions exist.

| Field | Contract |
| --- | --- |
| `schema_version` | Integer `1`; a boolean is invalid. |
| `meeting.date` | Canonical Gregorian `YYYY-MM-DD` string or null. |
| `meeting.timezone` | Nonempty declared timezone string or null; zone names are not validated. |
| `id` | Unique nonempty string. |
| `action` | Nonempty task text. |
| `status` | `committed` or `proposed`. |
| `owner` | Nonempty owner string or null. Null generates a review item. |
| `due_text` | Nonempty original deadline phrase or null. |
| `due_date` | Canonical Gregorian `YYYY-MM-DD` string or null. Null generates a review item. |
| `resolution_basis` | Nonempty explanation of date resolution or null. |
| `source.start_line`, `source.end_line` | Integers excluding booleans; one-based inclusive, positive, ordered, within the transcript. |
| `source.quote` | Nonempty exact text occurring within that line span; multiline quotes are allowed. |

A context-free `due_date` is allowed only when the same canonical ISO token appears in `due_text`. A different explicit ISO date is rejected. If `due_text` has no explicit ISO token (including null), a resolved `due_date` requires non-null valid meeting date, nonempty meeting timezone and nonempty resolution basis. The helper checks those declarations, not their truth. It does not calculate or choose dates from natural language. If a phrase includes multiple dates or relative qualifications, the agent must still explain the selected deadline and flag ambiguity.

Quote presence alone cannot prove semantic agreement: review the surrounding transcript to establish the task, commitment, owner and original deadline phrase. A tiny quote that omits the commitment or deadline is inadequate even when the checker accepts it. Use sufficient context to make the action reviewable.

## Output and exit codes

`--format json` returns `schema_version`, action count `actions`, `issues` and `review_items`. Each review item contains `id`, `field` (`owner` or `due_date`) and `reason`. `--format text` displays the same findings as readable lines; text is the default.

- `0`: no validation issues. Review items may remain.
- `1`: parsed JSON has invalid structure, date metadata, line bounds or quote evidence.
- `2`: usage, unreadable/non-UTF-8 input or JSON parsing error; diagnostic on stderr.

No external messages, events, tickets or system updates are performed. Output file creation belongs to the agent workflow and must use unused destinations.
