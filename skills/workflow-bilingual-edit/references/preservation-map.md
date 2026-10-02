# Literal preservation map

The checker accepts a JSON object with integer `schema_version: 1` and a nonempty `items` array. Each item contains:

| Field | Contract |
| --- | --- |
| `id` | Unique nonempty string identifying the claim or term. |
| `source` | Nonempty literal copied exactly from source text. |
| `target` | Nonempty literal copied exactly from edited text. |
| `kind` | One of `number`, `date`, `name`, `status`, `term`, `other`. |
| `factual_change` | Optional boolean, default false; true for a user-authorized factual change. |
| `explanation` | Optional nonempty string; required when factual_change is true. State what changed and the user instruction/evidence that authorized it. |

Example with invented names:

```json
{
  "schema_version": 1,
  "items": [
    {"id": "project", "source": "青灯项目", "target": "Qingdeng Project", "kind": "name"},
    {"id": "latency", "source": "12 ms", "target": "12 ms", "kind": "number"},
    {"id": "stage", "source": "尚未提交", "target": "has not been submitted", "kind": "status"}
  ]
}
```

For English-to-Chinese editing, source literals are English and target literals are Chinese. For same-language editing they can match or differ. Choose complete quantities such as `12 ms` or `8 synthetic samples`, rather than a digit that also appears in dates. Map related anchors separately when they represent distinct facts; evidence counts are independent and may overlap across items.

Counting uses exact, case-sensitive, non-overlapping Python `str.count` occurrences. Whitespace, punctuation and Unicode spelling are significant; no normalization or word-boundary matching occurs. Equal counts require both literals to occur at least once. An anchor absent from both texts is still a finding. Use enough context to distinguish identical numbers associated with different subjects, then review that association semantically.

JSON stdout contains `schema_version`, `scope`, `evidence` and `issues`. Evidence records each item and its `source_count`/`target_count`, retaining factual-change metadata. Issue codes are `source_missing`, `target_missing`, `count_mismatch`. Text output displays counts and findings. Exit 0 is structural literal evidence only; 1 reports anchor findings; 2 reports invalid schema, duplicate IDs or JSON keys, malformed/deep JSON, unknown kinds, UTF-8 errors, missing inputs, usage or output I/O errors. Input errors appear on stderr; findings appear on stdout. No input or output artifact is written by the helper.

The map does not establish that a translation is faithful, facts are true, authorization exists, or all important facts are covered. For instance, replacing “not approved” with “approved” can retain an `approved` literal and count while reversing meaning. Review complete clauses and their context, including units, uncertainty and stage, before delivery.
