#!/usr/bin/env python3
"""Plant the next typo in the relay and credit the person who found the last one.

This exists because the relay is a manual step, and a manual step on a farm is a step that
eventually stops happening. `tools/validate_seed.py` makes forgetting it a red build; this makes
remembering it a thirty second job, which is the half that actually keeps it alive.

It refuses three things, each of which would be worse than not planting a seed at all:

  * Planting while the current seed is still live, which would put two typos on a page that
    tells the reader there is one.
  * Planting the SAME misspelling that was just fixed. That reads as reverting the contributor's
    work, and `git blame` would show us breaking the exact word they repaired. Use a different
    word in a different sentence.
  * Planting anywhere `validate_seed.py` would reject. The gate is the oracle here rather than a
    second set of rules that can drift away from it.

Usage, after merging a fix:

    python3 tools/plant_seed.py --credit @handle --fixed recieve \
        --correct permanent --misspell permenant --dry-run

`--fixed` is the misspelling that was just repaired. It is checked against the retired seed's hash
before anything is written, so the chain records the word that was actually fixed instead of
whatever the person running this believed it was.
"""
import argparse
import datetime
import hashlib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validate_seed as gate  # noqa: E402  (path has to be set before this import)

ROOT = gate.ROOT
LEDGER = gate.LEDGER
PLACEHOLDER = re.compile(r"^\|\s*_\d+ is still live.*$", re.M)


def digest_of(word):
    return hashlib.sha256(word.lower().encode("utf-8")).hexdigest()


def seed_is_clean(markup, digest):
    """True when `markup` carries exactly one occurrence of the word, in safe prose."""
    parser = gate._Prose()
    parser.feed(markup)
    prose = parser.text()
    in_prose = gate.matches(prose, digest)
    if len(in_prose) != 1:
        return False
    if len(gate.matches(markup, digest)) != 1:
        return False
    word, start, end = in_prose[0]
    return not gate.UNSAFE_NEIGHBOUR.search(gate.neighbour_of(prose, start, end))


def plant(markup, correct, misspell):
    """Replace one whole-word `correct` with `misspell`, choosing an occurrence the gate accepts.

    Every candidate is tried in document order and judged by running the real check against the
    result, so this cannot produce a file that CI then rejects.
    """
    new_digest = digest_of(misspell)
    pattern = re.compile(r"\b{}\b".format(re.escape(correct)))
    spots = [m.span() for m in pattern.finditer(markup)]
    if not spots:
        return None, "{!r} does not appear in the page, so there is nothing to misspell.".format(
            correct)
    for start, end in spots:
        candidate = markup[:start] + misspell + markup[end:]
        if seed_is_clean(candidate, new_digest):
            return candidate, None
    return None, ("every occurrence of {!r} is somewhere a seed may not go (an attribute, a link, "
                  "a code block or a marker), or the word already appears elsewhere on the page. "
                  "Pick a different word.".format(correct))


def update_ledger(body, old_number, new_number, new_digest, credit, today, fixed_word):
    row = "| {} | `{}` | {} | {} |".format(old_number, fixed_word, credit, today)
    if PLACEHOLDER.search(body):
        body = PLACEHOLDER.sub(row, body, count=1)
    else:
        # Newest first, so the new row goes directly under the table's separator line.
        body = re.sub(r"(\|---\|---\|---\|---\|\n)", r"\1" + row + "\n", body, count=1)
    body = re.sub(r"(^\s*number:\s*)\S+", r"\g<1>{}".format(new_number), body, count=1, flags=re.M)
    body = re.sub(r"(^\s*sha256:\s*)\S+", r"\g<1>{}".format(new_digest), body, count=1, flags=re.M)
    body = re.sub(r"(^\s*planted:\s*)\S+", r"\g<1>{}".format(today), body, count=1, flags=re.M)
    return body


def main():
    ap = argparse.ArgumentParser(description="Plant the next seed in the typo relay.")
    ap.add_argument("--credit", required=True,
                    help="who fixed the seed being retired, e.g. @octocat, or 'anonymous' if they "
                         "asked not to be named")
    ap.add_argument("--fixed", required=True,
                    help="the misspelling that was just repaired, e.g. recieve. Checked against "
                         "the retired seed's hash so the chain cannot record the wrong word")
    ap.add_argument("--correct", required=True,
                    help="a correctly spelled word already on the page, to be misspelled")
    ap.add_argument("--misspell", required=True, help="how to misspell it")
    ap.add_argument("--dry-run", action="store_true", help="say what would change and write nothing")
    args = ap.parse_args()

    number, relpath, old_digest = gate.read_ledger()
    target = os.path.join(ROOT, relpath)
    with open(target, encoding="utf-8") as fh:
        markup = fh.read()

    parser = gate._Prose()
    parser.feed(markup)
    if gate.matches(parser.text(), old_digest):
        sys.exit("seed {} is still live in {}. Merge a fix before planting the next one, or the "
                 "page will carry two typos while claiming it carries one.".format(number, relpath))

    if digest_of(args.fixed) != old_digest:
        sys.exit("--fixed {!r} does not match the hash recorded for seed {}. Either that is not "
                 "the word that was fixed, or the ledger is out of date. The chain is a permanent "
                 "public record, so this refuses to guess.".format(args.fixed, number))

    if digest_of(args.misspell) == old_digest:
        sys.exit("{!r} is the misspelling that was just fixed. Planting it again reads as "
                 "reverting the contributor's work. Choose a different word in a different "
                 "sentence.".format(args.misspell))

    if args.correct.lower() == args.misspell.lower():
        sys.exit("--correct and --misspell are the same word.")

    updated, why = plant(markup, args.correct, args.misspell)
    if why:
        sys.exit("cannot plant: " + why)

    today = datetime.date.today().isoformat()
    new_number = int(number) + 1
    with open(LEDGER, encoding="utf-8") as fh:
        ledger = fh.read()
    # The retired seed's word is public the moment it is fixed, so the chain row spells it out.
    ledger = update_ledger(ledger, number, new_number, digest_of(args.misspell), args.credit,
                           today, args.fixed)

    print("seed {} retired, credited to {}".format(number, args.credit))
    print("seed {} planted: {!r} -> {!r} in {}".format(new_number, args.correct, args.misspell,
                                                       relpath))
    if args.dry_run:
        print("\n--dry-run, nothing written.")
        return 0

    with open(target, "w", encoding="utf-8") as fh:
        fh.write(updated)
    with open(LEDGER, "w", encoding="utf-8") as fh:
        fh.write(ledger)

    print("\nInspect it, then publish so the live page matches the repository:")
    print("    git diff")
    print("    python3 tools/validate_seed.py --require-live")
    print("    PROD_CONFIRM=1 SITE_URL=https://shipleyfarmsbeef.com \\")
    print("      python3 ../launch-automation/prod-queue/360_helloworld_page.py --apply")
    return 0


if __name__ == "__main__":
    sys.exit(main())
