# Unicode Gaps

Expose selected invisible or unusual spacing characters in literal UTF-8 text,
source code or logs before copying, comparing or publishing it. This standalone
Python 3.10+ tool uses only the standard library. No installation is needed.

From the repository root:

```sh
python3 -B line-2/tools/unicode-gaps/unicode_gaps.py --demo --max-details 2
```

The synthetic demo has **6 findings, 2 retained details and 4 omitted**: a
nonbreaking space, zero-width space, combining grapheme joiner, variation
selector, Unicode line separator and tab. Each retained detail gives its code
point, Unicode name/category, original UTF-8 byte range, exact bytes in hex,
line/byte column and up to 16 original context bytes per side. The full input's
SHA-256 and Python Unicode database version are reported. Counts are computed
over the complete input, independently of the detail cap.

Inspect an explicit real file:

```sh
python3 -B line-2/tools/unicode-gaps/unicode_gaps.py --file gathering/REPORT.md
```

This actual report was reviewed locally with no covered characters. Together
with the existing Unicode Lantern and Bidi Scope sources, its precise observed
byte counts, digests and reports are saved in `line-2/round-32-real-review.json`.
These are source reviews, not evidence of an attack or safety endorsements.

Coverage is deliberately explicit: runtime Unicode categories Cf and Zs/Zl/Zp
(except ordinary ASCII space), U+034F, U+FE00..FE0F, U+E0100..E01EF and ASCII
tab. This extends the existing line tools with evidence for format characters,
spacing and selectors; it neither replaces their lookalike checks nor analyzes
bidi scopes. Joiners and variation selectors often matter in legitimate scripts
and emoji. Findings require human interpretation. Many other combining marks,
default-ignorable characters and rendering tricks are outside this selection.

All CLI output is printable ASCII and LF only. Excerpts use `\xHH` for bytes
outside printable ASCII and double literal backslashes; JSON adds another
quoting layer. Excerpts can split UTF-8 characters and are unredacted. Source
labels are JSON escaped too. This is terminal-safe presentation, not HTML or
Markdown sanitization. Do not execute or unescape excerpts as instructions.

Coordinates are zero-based half-open original byte ranges, with one-based lines
and byte columns. **Only LF advances the line**; CR, Unicode line separators and
paragraph separators remain bytes on that LF-defined line. No language escapes
are decoded: the six literal characters `\u200b` are not a zero-width space.
No normalization, rewriting, language parsing or rendering prediction occurs.

Inputs must resolve to regular UTF-8 files within the current working directory,
at most 2 MiB. The detail cap is 1–1000 (default 100). The complete scan's totals
remain available when details are omitted. There is no recursive discovery,
network, environment access, modification, signing or sending. Copy just this
folder anywhere for standalone operation. File selection is confined to the
working directory; callers must choose inputs they are allowed to inspect.

Exit codes: **0** for the demo or a file without covered characters, **1** for a
selected file with findings, **2** for invalid input/error, with empty stdout and
an escaped JSON error on stderr. SHA-256 identifies bytes, not their author or
authenticity.

```sh
python3 -B -m unittest discover -s line-2/tools/unicode-gaps -p 'test_*.py' -v
```

All **14 tests passed**, including original CRLF/multibyte coordinates, exact
citations, supplementary variation selectors, inert terminal output, invalid
UTF-8, a full 2 MiB input, complete counts under truncation, 100 seeded independent
byte-position comparisons, path escape rejection and a copied standalone CLI.
Test fixtures stay in `test/scratch/`.
