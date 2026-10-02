# CobaltRoute synthetic experiment report

## Source and definitions

This demonstrates reporting from fictional values; it is not an executed experiment. The specification is [protocol.md](protocol.md), and the raw source is [results.jsonl](results.jsonl), SHA-256 `02c8a2a532cf614b9c80e3eeac5a4c893b7d455b303624a1675349b48631b5a8`. The machine-readable result is [summary.json](summary.json).

Protocol `cobalt-offset-v1` specifies five expected cases (`e01`–`e05`). Metric `offset_points` is a signed calibration offset in `points`. The specification defines neither a quality threshold nor a favorable direction. Expected count comes from the specification, not the four available rows.

## Methodology and denominators

Each unique case ID contributes one row. Numeric metrics, including zero and negative values, count as returned measurements. A null metric explicitly records a failed measurement; an absent expected row counts as missing. No row was dropped, source edited or new run fabricated.

| Count | Value |
| --- | ---: |
| Expected cases | 5 |
| Observed rows | 4 |
| Returned measurements | 3 |
| Explicit failed measurements | 1 |
| Missing expected cases | 1 |

Measurement coverage is **3/5 = 0.6 (60%)**. Conditional summaries use the **three returned measurements**, 2.5, 0 and -1, as their denominator; the explicit null and the missing expected case contribute neither zeros nor measurements.

| Conditional statistic | Points |
| --- | ---: |
| Mean | 0.5 |
| Median | 0 |
| Minimum | -1 |
| Maximum | 2.5 |

## Interpretation and limitations

Case `e04` explicitly lacks a measurement; `e05` has no row. Their offsets are unknown, so the conditional mean does not describe all five expected cases. Returning a measurement does not prove case correctness or quality. No improvement direction, causal effect, uncertainty, significance or generalization follows from this fixture. No comparison run is supplied.

The helper validates IDs, numeric tokens and counts; it cannot verify the caller's protocol definition or case membership against the specification. A future comparison would require matching protocol, metric/unit, expected population and denominator/missingness rules.

Integer inputs and integral aggregates remain exact. Decimal float tokens require a finite decimal-value round trip. Nonintegral aggregates use binary64 rounding, and nonfinite output or nonzero-to-zero underflow is rejected. These fixture values and the mean 0.5 are represented exactly; the displayed coverage fraction is rounded under the helper's general numeric contract.

Reproduction (stdout only; use exclusive creation for saved outputs):

```sh
python skills/workflow-experiment-report/scripts/summarize_results.py \
  examples/experiment-report/results.jsonl --metric offset_points \
  --expected-cases 5 --unit points --protocol cobalt-offset-v1
```
