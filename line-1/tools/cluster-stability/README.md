# Cluster Stability

Show how a paired benchmark's **whole-cluster** verdict changes when each
declared group is removed in turn. This helps a worker see whether the full-data
comparison depends on one group of related cases. Unlike Cluster Influence,
the p-values here use Cluster Verdict's whole-cluster sign-flip model throughout.
The complete original analysis and candidate family remain in the report.

Python 3.10+, standard library only. Copy this entire folder for offline use;
no packages, sibling tools or network are needed. From the repository root:

```sh
python3 -B line-1/tools/cluster-stability/cluster_stability.py --demo
```

When tried, the explicitly synthetic seven-group example gave both candidates
full-data Holm-adjusted p = **1/32**, rejecting at alpha 0.05. Removing **any**
group changed both decisions: adjusted p became **1/16**, without changing the
positive effect or direction. All seven deletions were checked. The example is
deliberately constructed to illustrate sensitivity, not measured improvement.

## Use your observations

Results are UTF-8 CSV with header `case,baseline,candidateA,candidateB` and two
through sixteen distinct named candidates. Every case has a unique ID and a
complete row of literal binary `0`/`1` outcomes. A second CSV with header
`case,cluster` must map every case exactly once into a disjoint nonempty group.
No unknown cases, duplicate assignments, blank rows or missing outcomes work.
IDs cannot have controls or edge whitespace. Quoted Unicode IDs, BOM and CRLF
are supported. Limits: 2–2000 cases, 2–128 clusters, and 2 MiB per file.

Retain both raw-file SHA-256 digests independently. Replace the descriptive
uppercase tokens with your actual paths and retained digests:

```sh
python3 -B line-1/tools/cluster-stability/cluster_stability.py --input RESULTS.csv --mapping GROUPS.csv --expected-input-sha256 RETAINED_RESULTS_DIGEST --expected-mapping-sha256 RETAINED_GROUPS_DIGEST --alpha 0.05 --max-details 20
```

Paths must resolve to regular files inside the current workspace. Alpha accepts
0.000001–0.2 and defaults to 0.05; use the planned value. `--max-details` accepts
0–128 and caps only deletion details. Every group is always reviewed, and the
complete full-data analysis, exact effect/p-value ranges, direction/decision
change counts and SHA-256 of all ordered deletion diagnostics remain. The digest
hashes compact sorted-key ASCII JSON for each complete deletion followed by LF;
it does not depend on the display cap. Original cluster details remain complete.

With only two original groups, removing one leaves too few groups for the
predecessor's supported inferential protocol. Effects and directions are still
reported, but deletion p-values, rejection decisions and decision-change counts
are **null**, with an explicit unavailable status. This is not non-rejection or
evidence of stability. Three or more original groups permit every deletion test.

Output goes only to stdout as ASCII-escaped JSON; no input is modified. Exit 0
means diagnostics completed, including unstable or unavailable results. Exit 2
means invalid input or pins, with no partial stdout. Redirection should use a new
filename. JSON labels require normal escaping when embedded in an HTML page.

## Existing measured workload

`policy-results.csv` and `policy-groups.csv` preserve the exact CSV strings from
the predecessor's `cluster-influence/measured-example.json`. They contain retained
observations of the three fixed JSON acceptance policies on eighteen curated
inputs. This step **did not reexecute the policies or certify those observations**.
`retained-policy-review.json` records the source file's digest, prior receipt pin,
and the new complete review. The data files make that review reproducible without
any sibling folder:

```sh
python3 -B line-1/tools/cluster-stability/cluster_stability.py --input line-1/tools/cluster-stability/policy-results.csv --mapping line-1/tools/cluster-stability/policy-groups.csv --expected-input-sha256 c8e80ed4104f4f85c50a2df9d02c2dbb6ca47fc748ad545815adfe6475226d02 --expected-mapping-sha256 9249247dc5141ec97400a4621181ff162c9d0c0ffa633ab2441fcc880fae3fab --max-details 128
```

When tried, neither candidate rejected under the asserted whole-cluster model,
and no group deletion changed that. Removing the nonfinite-constants group made
the constants guard tie the baseline. The unique/finite policy's adjusted p-value
varied from 1/2 to 1; its case-weighted effect ranged from 2/7 to 2/3. The five
categories are **post hoc illustrative groupings**, not registered independent
clusters. This is review of retained local evidence, not population inference.

## Calculation and interpretation

For each candidate and group, sum `candidate_pass - baseline_pass`. Under the
asserted null, whole-group differences have independent fair signs conditional
on their magnitudes. A justified whole-group randomized swap under a sharp null,
or an independent sign-symmetric cluster-difference model, can supply this.
Independent groups alone or zero mean alone cannot; a mapping cannot prove it.
All assumptions in the retained full-data Cluster Verdict report still apply.

The exact two-sided test counts sign assignments whose absolute sum is at least
the observed absolute sum, including ties. Zero group differences contribute no
sign information. For each deletion, Holm correction uses the **entire original
candidate family** and exact fractions, with the same fixed alpha. Effects weight
the remaining cases equally; large groups retain more weight than small ones.

The new implementation builds the subset-sum polynomial
`product(1 + x**abs(d))` once per candidate. Removing a nonzero difference `w`
divides out its factor using the exact recurrence `q[s] = f[s] - q[s-w]`.
Zero differences leave the distribution unchanged. Integer multiplicities are
checked for nonnegativity and conservation. All deletion p-values cost
O(groups × total absolute difference) integer operations per candidate, rather
than rebuilding every sign distribution. There is no sampling or float rounding.

Deletions overlap and are **sensitivity diagnostics**, not corrected new claims
or permission to omit inconvenient observations. Keep the full-data result.
Fix the case set, pass rule, partition, family, alpha and analysis before viewing
outcomes. Do not select deletions or groupings to improve significance. Stability
under one deletion covers neither multiple deletions, incorrect grouping,
selection, dishonest outcomes nor representative sampling. Non-rejection is not
equivalence; two-sided rejection may mean a loss and does not establish practical
value. Pins establish byte identity, not authorship or preregistration time.

## Checks and reuse

```sh
python3 -B -m unittest discover -s line-1/tools/cluster-stability -v
```

Eleven tests passed: exhaustive small sign vectors, 150 seeded unequal-magnitude
vectors, 128-group exact integer precision, 60 seeded full families checked
against independent sign enumeration and fresh reduced-CSV analyses, the decision
boundary, two-group unavailability, cancellation, exact ranges, Unicode/quotes,
BOM/CRLF, display caps, mapping order, budgets/types, pins, symlink escapes,
input immutability, retained measurement replay and a standalone copied-folder
CLI. Local checks are not independent statistical or execution certification.

`verdict_engine.py`, `grouping_engine.py` and `ladder_engine.py` are unchanged
ordinary source snapshots from Cluster Verdict; `provenance.json` pins them.
The first validates and retains the full original analysis; its exact Holm rule
is reused for deletions. No case-level McNemar calculation is used. No currency,
price, balance, pool, network, key, wallet, environment variable, signing,
sending, posting, payment or deployment is needed.
