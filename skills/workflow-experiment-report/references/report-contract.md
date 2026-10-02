# Results and report contract

## Input and invocation

`scripts/summarize_results.py RESULTS_JSONL --metric NAME --expected-cases N --unit UNIT --protocol LABEL [--format json|markdown]`

Each nonempty source line is one JSON object. Blank lines, malformed JSON, duplicate object keys and invalid UTF-8 are errors. JSON nesting exceeding the runtime decoder limit is also an input error (exit 2, without a traceback); no portable fixed depth limit is promised. An empty file is valid when N > 0: it represents no observed rows.

Each row requires:

- `id`: a unique nonempty string or integer, excluding booleans. Whitespace-only strings and float IDs are invalid. Integer `1` and string `"1"` are distinct identities. Preserve case ID types across sources.
- The literal metric key supplied through `--metric`: a JSON integer, finite decimal float or null. Null explicitly records a failed measurement; omitting the key is invalid. Booleans, strings, arrays and objects are invalid metrics. Extra fields are allowed and do not change the summary.

Expected N must be a positive integer at least as large as the observed row count. The metric, unit and protocol must be nonempty strings. Their correctness is the caller's responsibility; the helper does not inspect an external protocol or verify case membership against a case registry.

Exit 0 emits a complete report to stdout, including the all-failed/empty-input cases. Exit 2 emits an explanatory error to stderr and no report for invalid data, usage, I/O or unsupported numeric precision. There is no exit 1 condition. Sources are read as bytes, hashed and decoded as UTF-8; the helper never mutates files or opens outputs.

## Denominators and schema

| Field | Meaning |
| --- | --- |
| `schema_version` | 1 |
| `source.path`, `source.sha256` | Source path as supplied; SHA-256 of exact source bytes |
| `metric`, `unit`, `protocol` | Raw labels supplied by the caller |
| `counts.observed` | All valid source rows, including explicit nulls |
| `counts.expected` | Caller-supplied expected population size |
| `counts.returned` | Rows containing valid numeric measurements |
| `counts.failed` | Rows with explicit null metric |
| `counts.missing` | Expected minus observed; absent rows, not null metrics |
| `coverage.numerator`, `.denominator`, `.fraction` | Returned, expected, returned/expected |
| `statistics.denominator`, `.population` | Returned count; returned measurements only |
| `statistics.mean`, `.median`, `.min`, `.max` | Descriptive statistics conditional on returned measurements; all null with no measurements |
| `statistics.exact.mean`, `.median` | Reduced rational metadata: integer `numerator`, positive integer `denominator`, and `serialized_numeric_is_exact`; each entry is null with no measurements |
| `numeric_precision` | Machine-output numeric contract |

Invariants: observed = returned + failed; expected = returned + failed + missing. These counts do not establish whether a returned measurement met an external quality criterion.

## Numeric contract

Integer tokens remain Python integers, including odd integers beyond binary64's exact mantissa range. Floats are accepted only when finite and `Decimal(raw_token) == Decimal(str(float(raw_token)))`. Equivalent spellings such as `0.10` and `1e-1` are allowed; decimal digits cannot silently disappear. For example, `0.1234567890123456789`, `9007199254740993.0`, `1e400` and `1e-400` are rejected. Nonstandard `NaN` and `Infinity` constants are rejected anywhere in a row. All float tokens, including extra fields, use the same parser. Exact `9007199254740993` is accepted as an integer. Runtime limits on extremely long integer strings can cause an explicit parsing error.

Statistics use exact rational arithmetic over the accepted decimal values, preventing intermediate overflow and cancellation loss. Min/max use those same rational comparison keys and preserve the original chosen numeric values. For example, the decimal value `1e23` exceeds integer `99999999999999999999999`, even though Python's internal binary float compares differently. Integral mean/median outputs stay exact JSON integers. Nonintegral aggregates remain JSON numbers rounded to binary64, including reportable repeating results such as 1/3. Coverage fractions are also rounded. Output overflow/nonfinite values and nonzero aggregates rounding to zero are rejected; valid finite integer datasets are not rejected merely because their mean or median rounds.

For mean and median, `statistics.exact` preserves the reduced numerator/denominator and declares whether the **serialized decimal numeric output** equals that rational. The flag compares `Fraction(str(number))` to the rational; it does not claim exact binary representation inside a float. For `[0, 2.4]`, mean/median `1.2` have ratio 6/5 and `serialized_numeric_is_exact: true`. For `[1, 0, 0]`, mean `0.3333333333333333` has ratio 1/3 and flag false. For `[9007199254740993, 9007199254740994]`, mean/median `9007199254740994.0` have exact ratio 18014398509481987/2 and flag false: the half unit must remain visible. Markdown labels differing outputs as rounded approximations beside their exact ratios. With no measurements both metadata entries are null.

Decimal round-trip safety does not imply exact binary representation of inputs such as 0.1. Downstream JavaScript/float-only consumers may round large exact JSON integers, including rational numerators/denominators: choose a decoder that preserves integer precision.

## Full written report

The Markdown helper output is a data summary. The agent adds methodology and evidence for protocol, expected cases and metric interpretation to `experiment-report.md`. Cite the existing experiment specification and source; disclose missingness, failed cases and precision limits. Preserve both denominators prominently. Statistical uncertainty or significance requires a separate justified analysis, which this helper does not perform. For cross-run comparisons, match protocol, metric/unit, expected population and denominator/missingness definitions first; a matching label alone does not prove a matching method.
