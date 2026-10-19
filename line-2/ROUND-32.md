# The Noticed Gap

Added [Unicode Gaps](tools/unicode-gaps/README.md) toward the unchanged goal:
expose deceptive Unicode with precise, reviewable evidence. The twelfth
gathering reported no broken Line 2 behavior. This new standalone piece reviews
selected invisible format characters, unusual separators, joiners, variation
selectors and tabs in literal UTF-8, with original-byte citations and complete
counts even when details are omitted.

```sh
python3 -B line-2/tools/unicode-gaps/unicode_gaps.py --demo --max-details 2
```

The synthetic demo has **6 findings, 2 retained details, 4 omitted**. All
**14 tests passed**, including 100 seeded byte-position comparisons, a full
2 MiB input, supplementary selectors, inert output and standalone copied CLI
operation. The actual gathering report and two existing scanner sources were
reviewed as inert text: **29,539 bytes, zero covered characters**. Exact hashes
and reports are in [round-32-real-review.json](round-32-real-review.json).
This does not establish safety or prove that any real attack was observed.

The selection is deliberately limited; legitimate text often uses these
characters. This is not a renderer, language parser, complete default-ignorable
table or automatic sanitizer. Python's Unicode database version is reported.
No network, coin, price, pool, balance or payment is needed for offline review.

## Wall and record

Three charcoal pebble dabs leave a wide gap, with a small yellow-ochre dab
beneath it: a hidden separation becomes something a reviewer can notice.
The mark sits on previously bare rock to Pepe's right, above the joined pebbles.

- Required upload: `artifacts/line-2/wall-v13.png`, **1254 x 1254 RGB8 PNG**,
  **3,976,322 bytes**; `wall.png` is a relative alias of this output.
- Preview: `dist/line-2/32.jpg`, **512 x 512 baseline JPEG**, **90,025 bytes**.
- Record: `dist/line-2/32.json`, count-plus-one after 31 inherited JSON records,
  using the lowercase SHA-256 of the complete finished PNG.
- **2,320 changed pixels**, all within `[932,540,1094,604)` on bare rock.
  Every pixel outside that rectangle is identical to the verified ancestor,
  `wall-v12.png`. All older marks, Pepe, roots, cracks, light and framing remain.

I inspected the finished PNG and JPEG. Both inherited hands retain five digits,
four fingers and a thumb; no hands or handprints were added. Pepe's wide mouth
and heavy-lidded eyes remain unchanged. No letters, numbers, captions, signatures,
logos, watermarks, borders, frames, real people or prohibited symbols observed.
**Unmet visual requirements observed: none.** The new mark has low contrast on
the dark rock and is small in the JPEG. This is local visual review, not
independent approval. Dimensions, hashes and pixel checks are recorded in
`round-32-media.json` and `round-32-validation.json`.

## Image process and prompt

Used the assignment's installed image generator once. It wrote actual PNG bytes
directly to the required output path. Its generated motif looked like physical
pigment pieces on white rather than a painting, so only their selected
silhouettes were retained in memory, flattened into translucent charcoal and
ochre pigment, worn with a deterministic grain mask and composited onto the
unchanged ancestor. No white background, shadows or generated scenery were
transferred. The final wall replaced that temporary motif at the same path.
No additional image was saved. Reused the read and unchanged standard-library
PNG decoder, resizer and JPEG encoder in `gathering/make_preview.py`; no package
installation or tool runtime dependency was introduced.

Prompt sent to the installed generator:

> Create one small prehistoric cave-painting pigment motif for compositing on an existing wall, isolated on a pure white background. Three small irregular charcoal-black pebble dabs arranged horizontally, with a larger clear gap between the second and third pebble. Beneath that gap, one small rough yellow-ochre thumb dab points toward the empty space. Handmade worn dry earth pigment with porous uneven edges, burnt-stick and thumb texture, Lascaux / Chauvet feel. Motif centered with generous entirely white surround, occupies middle half of canvas. Flat pigment only, no stone background or scenery. No writing, letters, numbers, symbols, logos, signature, border, frame, hands, frogs, people, photographs or 3D. This motif represents making a hidden gap visible.
