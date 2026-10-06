# The typo relay

`helloworld.html` always contains exactly one deliberate misspelling. When somebody fixes it, a
maintainer plants the next one, and the person who fixed it gets a row in the chain below.

This file is the ledger. It exists so the relay cannot quietly stop: CI reads it, and **`main`
goes red the moment a seed has been fixed and not replaced.** A forgotten relay is a build
failure rather than a slow disappointment for the next person who comes looking.

## Current seed

```
number:  4
file:    site/helloworld.html
sha256:  3fcc6a41647fc6fccbec53222e9a6103f877280857e07f0886d39573a7f38ae4
planted: 2026-10-06
```

The word itself is stored as a SHA-256 hash rather than in plain text, because writing it here
would hand away the puzzle to anyone who reads the repository before the page.

This is deliberately weak protection. A hash of an ordinary English misspelling falls to a
wordlist in seconds, and that is fine: if you would rather solve this by hashing a dictionary
than by reading a paragraph, you have done something more interesting than finding a typo, and
we would like to see that script. Send it as a pull request to `examples/`.

## Where a seed is allowed to be

A seed goes in ordinary prose, in a sentence a person reads. It may never sit in any of these,
because a "typo" in one of them is a defect and not a game:

- an attribute value, a URL, or an email address
- anything inside `<code>`, `<script>` or `<style>`
- a `SHIPLEY_*_V1` publisher marker
- a product name or a price
- the invitation paragraph itself, or any of the text `tools/validate_site.py` requires

`tools/validate_seed.py` enforces the first four mechanically. The last two are judgement, so
read the page before you plant.

## The chain so far

Newest first. Each row is a real merged pull request against a live page.

| # | Misspelling | Found and fixed by | Merged |
|---|---|---|---|
| 3 | `buisness` | @O1sumitkumar | 2026-10-06 |
| 2 | `catagory` | @aipd506 | 2026-10-02 |
| 1 | `recieve` | @Jah-yee | 2026-09-30 |

## For maintainers

After merging a fix, plant the next seed in the same commit range, not "later":

```
python3 tools/plant_seed.py --credit @their-handle --fixed recieve \
    --correct permanent --misspell permenant
```

That rewrites the page, updates the block above, moves the fixed seed into the chain, and prints
the publish command. Then run the publisher so the live page matches the repository, because a
merged fix that is never published makes a liar out of the page.
