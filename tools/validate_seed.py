#!/usr/bin/env python3
"""Keep the typo relay running, and keep a planted typo somewhere harmless.

`site/helloworld.html` carries exactly one deliberate misspelling as a first task for someone who
has never opened a pull request. The relay only works if somebody plants a fresh one each time the
old one is fixed, and the honest failure mode of a manual step on a farm is that it stops
happening. So this is a gate rather than a note in a README.

Two checks, and they run in different directions on purpose:

  ON A PULL REQUEST, a seed is allowed to be missing. That is what a fix looks like, and failing
  the contribution we asked for would be absurd. What is NOT allowed is a SECOND seed appearing,
  or the seed moving somewhere it can do damage.

  ON main (--require-live), a missing seed IS the failure. Once a fix is merged the repository
  owes the next person a way in, and this turns that debt into a red build instead of a page that
  quietly invites people to find a typo that is no longer there.

The seed is recorded in `site/SEEDED.md` as a SHA-256 hash, so this file can verify the invariant
without printing the answer. See that file for why the weak protection is deliberate.

    python3 tools/validate_seed.py                 # pull request mode
    python3 tools/validate_seed.py --require-live   # main mode
"""
import hashlib
import html.parser
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "site", "SEEDED.md")

# Text inside these never counts as prose. A misspelling in any of them is a defect, not a game.
OPAQUE = ("code", "script", "style", "pre", "kbd", "samp")

WORD = re.compile(r"[A-Za-z][A-Za-z']*")
# A run of non-space characters around a match. If it carries any of these, the word is part of an
# address, a link or a figure rather than part of a sentence.
UNSAFE_NEIGHBOUR = re.compile(r"[@$]|://|\d")


class _Prose(html.parser.HTMLParser):
    """Collect only the text a reader reads.

    Attribute values are never collected: HTMLParser hands them over separately and this class
    simply does not look at them, which is what makes "never in an attribute" true by
    construction rather than by a regex that has to anticipate every attribute name.
    """

    def __init__(self):
        html.parser.HTMLParser.__init__(self, convert_charrefs=True)
        self.chunks = []
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in OPAQUE:
            self._depth += 1

    def handle_endtag(self, tag):
        if tag in OPAQUE and self._depth:
            self._depth -= 1

    def handle_data(self, data):
        if not self._depth:
            self.chunks.append(data)

    def handle_comment(self, data):
        pass  # A marker comment is not prose. SHIPLEY_HELLOWORLD_V1 must never hold the seed.

    def text(self):
        return " ".join(self.chunks)


def read_ledger():
    """Return (number, relative_path, sha256) from the Current seed block, or exit explaining."""
    if not os.path.exists(LEDGER):
        sys.exit("no site/SEEDED.md. That file is the relay's ledger; this gate cannot run "
                 "without it. Restore it rather than deleting this check.")
    with open(LEDGER, encoding="utf-8") as fh:
        body = fh.read()
    fields = {}
    for key in ("number", "file", "sha256"):
        hit = re.search(r"^\s*{}:\s*(\S+)\s*$".format(key), body, re.M)
        if hit:
            fields[key] = hit.group(1)
    missing = [k for k in ("number", "file", "sha256") if k not in fields]
    if missing:
        sys.exit("site/SEEDED.md is missing {} in its Current seed block. The block is parsed by "
                 "this script, so keep the 'key: value' shape.".format(", ".join(missing)))
    if not re.fullmatch(r"[0-9a-f]{64}", fields["sha256"]):
        sys.exit("site/SEEDED.md sha256 is not 64 hex characters. Use "
                 "tools/plant_seed.py, which writes it for you.")
    return fields["number"], fields["file"], fields["sha256"]


def matches(text, digest):
    """Every distinct word in `text` whose lowercased SHA-256 is `digest`, with its spans."""
    found = []
    for m in WORD.finditer(text):
        word = m.group(0)
        if hashlib.sha256(word.lower().encode("utf-8")).hexdigest() == digest:
            found.append((word, m.start(), m.end()))
    return found


def neighbour_of(text, start, end):
    """The whitespace-delimited run containing text[start:end]."""
    left = start
    while left > 0 and not text[left - 1].isspace():
        left -= 1
    right = end
    while right < len(text) and not text[right].isspace():
        right += 1
    return text[left:right]


def main():
    require_live = "--require-live" in sys.argv[1:]
    number, relpath, digest = read_ledger()

    target = os.path.join(ROOT, relpath)
    if not os.path.exists(target):
        sys.exit("site/SEEDED.md points at {}, which does not exist.".format(relpath))
    with open(target, encoding="utf-8") as fh:
        markup = fh.read()

    parser = _Prose()
    parser.feed(markup)
    prose = parser.text()

    in_prose = matches(prose, digest)
    everywhere = matches(markup, digest)

    problems = []

    # Somewhere forbidden: present in the raw file more often than in the prose, which means at
    # least one occurrence is in an attribute, a marker comment, or an opaque element.
    if len(everywhere) > len(in_prose):
        problems.append(
            "seed {} appears outside prose ({} time(s) in the file, {} in readable text). A "
            "planted typo in an attribute, a URL, a marker comment or a <code> block is a real "
            "defect. Move it into a sentence.".format(number, len(everywhere), len(in_prose)))

    for word, start, end in in_prose:
        run = neighbour_of(prose, start, end)
        if UNSAFE_NEIGHBOUR.search(run):
            problems.append(
                "seed {} sits inside {!r}, which looks like an address, a link or a figure. A "
                "seed belongs in a plain sentence.".format(number, run.strip()))

    if len(in_prose) > 1:
        problems.append(
            "{} live seeds, and there must be exactly one. The page tells the reader there is "
            "'exactly one spelling mistake', so a second one makes the page untrue and wastes "
            "the next contributor's time.".format(len(in_prose)))

    if not in_prose:
        if require_live:
            problems.append(
                "seed {} is gone from {} and nothing replaced it. Somebody's fix has landed, so "
                "the repository now owes the next person a way in. Plant the next seed:\n"
                "      python3 tools/plant_seed.py --credit @handle --correct <word> "
                "--misspell <typo>".format(number, relpath))
        elif not problems:
            # A clean fix in flight. Only say so when nothing else is wrong: a seed that vanished
            # from the prose and reappeared in an attribute is NOT a fix, and reporting it as one
            # is how a hidden defect gets merged with a green tick.
            print("  seed {:<3} fixed in this change, not yet replaced   OK".format(number))
            print("\nA maintainer plants the next seed when this merges. Nothing for you to do.")
            return 0

    if problems:
        print("\n{} problem(s):\n".format(len(problems)))
        for p in problems:
            print("  * " + p)
        print("\nsite/SEEDED.md explains where a seed may and may not go.")
        return 1

    print("  seed {:<3} live in {:<22} OK".format(number, relpath))
    return 0


if __name__ == "__main__":
    sys.exit(main())
