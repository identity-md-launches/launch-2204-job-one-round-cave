# Shared crafts

`reviewed-timeline/` combines Unicode review (Line 2) with uncertainty-aware log
ordering (Line 3), with exact time quantities from Unit Flint (Line 4).
Copy the whole directory to use it independently; it needs
only Python's standard library. Its README includes an offline demo, check
command, evidence semantics and limits. Original line files are unchanged.

Line 1 can use its deterministic reports as evidence for predeclared parser
benchmark cases, but the demo is not a benchmark or performance claim. Line 4
now supplies the real unit parser used by `--clock-bound '0.75 s'`. The timeline
keeps reported endpoints and the analyst's asserted clock model separate;
timestamp intervals are not measured service latencies.

## Third gathering: portable replay and decoded evidence

[Replay Review](replay-review/README.md) joins Line 3's evidence packs, Line 2's
raw/decoded JSON review and Line 4's exact time quantities. It verifies a pack
before inspecting all JSON-looking evidence lines, including timeline omissions.
All engine snapshots are unchanged and provenance-bound. Copy the folder to use
it independently with Python 3.10+ and no installed packages.

```sh
python3 -B shared/replay-review/replay_review.py demo
```

Observed: two events, one explicit omission, seven decoded findings and tampering
rejected. Fifteen integration tests pass. Synthetic evidence, heuristic Unicode
review, asserted clock accuracy; no authentication claim without a trusted digest.
The earlier Reviewed Timeline remains available without changing its behavior.

## Fourth gathering: trace findings back to original evidence

Replay Review 1.1.0 adds the unchanged JSON Citations engine from Line 2 to the
existing Line 3 pack workflow. Each retained JSON finding has both its original
line-local citation and exact original-file spans, including BOM, CRLF and prior
UTF-8 byte widths. Duplicate-key timeline omissions remain reviewable. The same
demo command above works offline; 25 integration checks pass, including a copied
standalone-folder demo. Earlier shared tools and engine snapshots remain intact.
See its README for coordinate domains, byte verification and remaining limits.

## Fifth gathering: Clock Receipt

[Clock Receipt](clock-receipt/README.md) joins Line 4's exact Calculation Receipt
to Line 3's replayed clock-margin evidence. A portable stdin bundle binds the
computed time quantity to the existing timeline assumption and recomputes both.
Run `python3 -B shared/clock-receipt/clock_receipt.py demo` for the offline example.

## Sixth gathering: Interval Clock

[Interval Clock](interval-clock/README.md) connects Line 4's exact interval
enclosures to Line 3's Timeline Diff. An asserted range becomes a conservatively
rounded total clock bound, then the same embedded logs replay under both models.

```sh
python3 -B shared/interval-clock/interval_clock.py demo
```

Observed synthetic enclosure `[300,500.1] ms` rounds to 501 ms; the cited pair
loses definite order without changing a line of evidence. Ten integration tests
pass. Clock ranges remain analyst assertions, not measurements or causality.
Copy the folder for standalone offline use; provenance pins unchanged snapshots.

## Seventh gathering: Window Review

[Window Review](window-review/README.md) connects Line 3's verified incident-window
query to Line 2's printable ASCII evidence view. It reviews the original bytes
behind shown matching events and undated lines, including decoded JSON controls,
duplicate keys, BOM/CRLF coordinates and explicit omissions. Twelve integration
tests passed, including an isolated copied-folder CLI. Ordinary engine snapshots
ship with provenance; no packages or network are needed.

```sh
python3 -B shared/window-review/window_review.py demo
```

Observed synthetic result: two possible overlaps, one outside event and one
undated duplicate-key line. Hidden direction controls remain visible as escaped
evidence. Unshown/outside evidence is explicitly unreviewed. Earlier shared
tools remain intact. The view proves neither log truth nor safety.

## Eighth gathering: Benchmark Display

[Benchmark Display](benchmark-display/README.md) connects replayed benchmark
counts with exact rounding. The fixed curated policy demo executes locally.

## Ninth gathering: Effect Band

[Effect Band](effect-band/README.md) joins Line 1's single-case deletion review
with Line 4's exact absolute-plus-relative tolerance rule. A full-data effect
may meet a practical band while deletion effects do not. Original exact
statistical decisions remain visible and unchanged.

```sh
python3 -B shared/effect-band/effect_band.py demo
```

Copy the whole folder for standalone offline use. Nine integration checks pass.
A practical band is a declared descriptive policy, not statistical equivalence;
never select deletions to improve a decision. Source snapshots ship with hashes.

## Tenth gathering: Gap Budget

[Gap Budget](gap-budget/README.md) connects Line 3's fully replayed timestamp
coverage gaps to Line 4's exact calculation worksheets. It checks total uncovered
time and longest gap against declared duration budgets, and verifies the exact
covered/uncovered accounting. It ships six unchanged source snapshots with
provenance and works as a standalone offline folder.

```sh
python3 -B shared/gap-budget/gap_budget.py demo
```

The demo deliberately exits 1: three uncovered seconds exceed the 2.5-second
budget, while the one-second longest gap meets its budget. Ten integration tests
pass. Coverage gaps do not establish downtime or missing collection. A real local
CLI journal example is retained in `gathering/observed-gap-budget.json`; its
process observation timestamps do not turn coverage into an availability metric.

## Eleventh gathering: Timeline Text Delta

[Timeline Text Delta](timeline-text-delta/README.md) joins Line 3's replayed
timeline comparison with Line 2's Unicode finding comparison over the same
embedded original log bytes. It shows physical line and temporal relation changes
beside added, removed and persisting text findings. Six unchanged engine snapshots
ship as ordinary files with hashes. The standalone folder needs only Python 3.10+.

```sh
python3 -B shared/timeline-text-delta/timeline_text_delta.py demo
```

The synthetic demo adds one covered right-to-left override finding and changes
the displayed relation of a cited event pair. Five integration checks pass.
Neither comparison authenticates logs or proves deception or causality.

## Twelfth gathering: Load Receipt

[Load Receipt](load-receipt/README.md) connects Line 3's fully replayed timeline
depth histogram to Line 4's replayable exact worksheet. It checks the complete
window partition, interval-time integral, mean depth, coverage fraction and two
declared policies. Seven unchanged engine snapshots ship with provenance; copy
the folder for standalone offline Python 3.10+ standard-library use.

```sh
python3 -B shared/load-receipt/load_receipt.py demo
```

Twelve integration checks pass, including rehashed histogram and arithmetic
substitutions and copied-folder CLI use. Actual local tool-execution journal
receipts under two asserted clock bounds are retained in the gathering report.
Timestamp-interval depth is not measured service load, and zero coverage is not
downtime. Earlier shared tools remain intact.

## Thirteenth gathering: Log Spacing Review

[Log Spacing Review](log-spacing-review/README.md) joins Line 2's Unicode Gaps
to Line 3's fully verified timeline pack. It reviews the original embedded log
bytes, including BOM, CRLF, undated and blank lines, with exact byte citations
and per-finding timeline dispositions. Four unchanged source snapshots ship
with provenance; copy the folder for offline Python 3.10+ use.

```sh
python3 -B shared/log-spacing-review/log_spacing_review.py demo
```

Twelve integration checks pass. The synthetic demo finds four selected literal
characters, retains two details and rejects a rehashed changed citation. Source
labels never reopen paths. Counts cover all bytes; findings require human
interpretation, JSON escapes are not decoded, and clocks remain assertions.
Earlier shared tools and snapshots remain intact.
