# Evidence ledger

Create `evidence-ledger.json`:

```json
{
  "claims": [
    {
      "id": "c1",
      "claim": "The offline run returned 28 of 30 cases.",
      "status": "provided",
      "evidence": [
        {
          "source": "brief.md",
          "locator": "Run summary, first bullet",
          "observation": "The user supplied 30 cases and 28 returned results.",
          "observed": true
        }
      ]
    }
  ]
}
```

Statuses:

- `supported`: the claimed fact is established by an actually observed source. Requires at least one evidence entry with `observed: true`.
- `provided`: the user or stakeholder supplied the fact; do not imply independent verification.
- `inference`: interpretation from evidence; name the inference in prose and record its basis.
- `unverified`: no adequate evidence; preserve the open item rather than fabricate it.

`source` is a local relative path or source URL; `locator` identifies a section/line/page; `observation` is a concise paraphrase of what was actually seen. Record retrieval/publication dates when temporally relevant. Observed metadata is an assertion made by the agent and must match its actions.

If conditional mean error improves but output coverage drops, report both and avoid claiming an unconditional accuracy improvement. A filename saying “final” is not approval evidence. A hypothetical URL cannot become a real citation.
