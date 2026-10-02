# CobaltRoute synthetic reporting fixture

This is fictional input for demonstrating report generation, not an executed experiment.

Protocol: `cobalt-offset-v1`. Expected cases: `e01`, `e02`, `e03`, `e04`, `e05` (5 total). Each case would return one `offset_points` measurement in `points`, describing a signed calibration offset. Zero and negative offsets are valid. No quality threshold or favorable direction is defined. Null marks an explicit failed measurement. A case without a source row is missing.

Only the four synthetic rows in `results.jsonl` are available. No repeated trials, uncertainty estimates, alternative protocol or comparison run are supplied.
