# Log Spacing Review

Replay an uncertainty-aware timeline and expose selected invisible characters,
unusual spacing, joiners, selectors and tabs in its exact embedded log bytes.
This carries Line 2's Unicode Gaps into Line 3's incident workflow. Copy this
entire directory anywhere; Python 3.10+ standard library only.

```sh
python3 -B shared/log-spacing-review/log_spacing_review.py demo
```

Observed: three synthetic events and one undated omission replay successfully.
Four selected characters appear in the original log: BOM, zero-width space,
nonbreaking space in the undated diagnostic, and tab. With two details per source,
two remain and two are omitted; complete counts stay four. The JSON log's literal
`\u200b` escape is outside literal-character coverage. A changed citation remains
rejected after its outer digest is recomputed.

For your own evidence, run from the workspace containing explicit incident logs:

```sh
python3 -B shared/log-spacing-review/engines/timeline_replay.py pack --ignore-unmatched incident.log > pack.json
python3 -B shared/log-spacing-review/log_spacing_review.py create --max-details 20 < pack.json > review.json
python3 -B shared/log-spacing-review/log_spacing_review.py verify < review.json
```

`create` and `verify` exit 1 when selected characters exist, 0 when none are covered,
and 2 for invalid evidence/errors with empty stdout. Finding exits mean review
work, not invalid evidence. The demonstration exits 0. Retain `receipt_sha256`
independently and use `verify --expected-sha256 <digest>` to reject replacement
by another internally valid receipt. The digest covers canonical content except
its own digest field, not JSON whitespace.

Verification recomputes the whole timeline and all source reviews; source labels
never reopen files. Every retained detail gives original zero-based half-open
file byte ranges, hex bytes, one-based LF line/byte column and a disposition:
`event`, `omitted`, or `blank-or-unrepresented`. The whole source is scanned,
including BOM, CRLF, undated and whitespace-only lines. Only LF advances line
numbers. Detail caps apply per source; counts cover all bytes. Timeline parsing
may strip BOM/CR while Unicode citations preserve original bytes.

Four unchanged engine files ship with hashes in `provenance.json`. Receipts pin
the wrapper and engines too. Input and combined output are bounded to 16 MiB;
underlying packs allow 2 MiB total raw logs and 64 sources. The per-source detail
cap is 1..1000. Duplicate JSON keys, nonfinite values and excessive nesting are
rejected. Output JSON escapes non-ASCII characters. Evidence is unredacted;
never execute or unescape excerpts.

Coverage is Unicode Cf; Zs/Zl/Zp except ordinary space; U+034F; variation selectors
U+FE00..FE0F and U+E0100..E01EF; tab. Findings are review candidates, not deception
verdicts or rendering predictions. Other risks are outside coverage. JSON escapes
are not decoded; use the earlier Replay Review for decoded JSON. Runtime Unicode
tables are recorded and different versions may prevent replay. Clock assumptions
are asserted; compatibility is not causality. Hashes prove neither log truth,
authorship nor creation time.

```sh
python3 -B -m unittest discover -s shared/log-spacing-review -v
```

All 12 integration tests passed: original citations, BOM/CRLF/omitted lines,
complete counts under caps, rehashed forgeries, detached reports, source drift,
independent pins, inert names, invalid input, blank sources and copied-folder CLI.
Fixtures stay in `test/scratch/`. The tool reads stdin and fixed shipped sources;
no packages, network, environment/configuration access, signing or sending.
