#!/usr/bin/env python3
"""Check the DCO sign-off on every commit in a pull request, and say what is wrong when one fails.

WHY THIS EXISTS. The gate this replaces was correct and unkind. It tested the sign-off with one
regex and then printed, unconditionally, "No Signed-off-by line." For a commit with no sign-off
that is true and useful. For a commit with a sign-off that is merely misformatted it is a
falsehood, and it sends the contributor away to fix something they already did.

That is not hypothetical. PR #15, 2026-10-18, @Sanika-M-Rangayyan, a correct one-word fix of
seed 5, byte-identical to the #16 that was later merged and credited. They signed off, in the
right box, with their real name and address:

    Signed-off-by: Sanika Rangayyan (sanika.rangayyan@gmail.com)

Round brackets instead of angle brackets. Two characters. The check went red fourteen seconds
after they opened the pull request, told them they had not signed off at all, and they closed
their own correct work four minutes and fifty seconds later. Nobody had spoken to them. Eighteen
hours later a different contributor sent the same bytes, went green, and took the credit. The
same thing cost us PR #12 twelve days earlier.

So this script's job is not to be stricter or looser. The rule is unchanged, deliberately: a
sign-off needs `Name <address>` with angle brackets, because that is what `git commit -s` writes
and what the DCO is understood to mean everywhere else. What changes is that a near miss is
diagnosed by name, with the corrected line printed back from what the contributor actually
typed, so the remedy is obvious and takes one edit.

WHAT IT WILL NEVER DO. It will not accept a malformed sign-off, and it will not add one. The
sign-off certifies that a human wrote the change and has the right to submit it, so a maintainer
forging it defeats the only thing it is for. `docs/MAINTAINING.md` step 3 is the standing rule:
ask, never add it yourself.

    python3 tools/check_signoff.py --range BASE..HEAD
    python3 tools/check_signoff.py --message-file msg.txt
    python3 tools/check_signoff.py --self-test
"""
import argparse
import re
import subprocess
import sys

# The accepted form, character for character the regex this script replaces:
#   grep -qi '^Signed-off-by: .\+ <.\+@.\+>'
# Kept identical ON PURPOSE. The point of this script is to explain a failure, not to move the
# line, so a commit that passed the old gate passes this one and a commit that failed still
# fails. Anchored at the start of the line with no leading whitespace allowed, because that is
# how git parses a trailer and how the old gate behaved.
VALID = re.compile(r"^signed-off-by: .+ <.+@.+>", re.I)

# Anything a person plausibly meant as a sign-off, so a near miss can be told apart from an
# absence. Deliberately loose: leading space, a missing hyphen, a missing colon.
NEARISH = re.compile(r"^[ \t]*signed[-_ ]?off[-_ ]?by[ \t]*:?", re.I)

BRACKETS = {"(": ")", "[": "]", "{": "}"}


def _diagnose(line):
    """Return a plain-language reason `line` is not a valid sign-off, and a corrected line."""
    indented = line[:1] in (" ", "\t")
    raw = line.strip()
    body = NEARISH.sub("", raw).strip()

    # Pull out an address wherever it sits, so the fix can be printed back to them.
    addr = None
    m = re.search(r"[^\s<>()\[\]{},;]+@[^\s<>()\[\]{},;]+", body)
    if m:
        addr = m.group(0).rstrip(".")
    name = None
    if addr:
        before = body[:body.find(addr)]
        name = before.strip(" \t<([{,;").strip()
        if not name:
            after = body[body.find(addr) + len(addr):]
            name = after.strip(" \t>)]},;").strip() or None

    fixed = "Signed-off-by: {} <{}>".format(name or "Your Name", addr or "your@email.com")

    if indented and VALID.match(raw):
        why = ("the line is indented. A sign-off has to begin at the very start of the line, "
               "with no spaces in front of `Signed-off-by:`. Everything else about it is right")
    elif not re.match(r"^signed-off-by:", raw, re.I):
        why = ("the trailer has to read exactly `Signed-off-by:`, at the very start of the line "
               "with nothing indented in front of it")
    elif addr and any(
            "{}{}{}".format(o, addr, c) in body for o, c in BRACKETS.items()):
        opener = next(o for o, c in BRACKETS.items() if "{}{}{}".format(o, addr, c) in body)
        why = ("the address is wrapped in `{}{}` and the DCO needs angle brackets, `<` and `>`. "
               "That is the whole problem: two characters".format(opener, BRACKETS[opener]))
    elif addr and "<" not in body and ">" not in body:
        why = "the address needs to be wrapped in angle brackets, `<` and `>`"
    elif addr and ("<" not in body or ">" not in body):
        why = "one of the angle brackets around the address is missing"
    elif not addr:
        why = ("there is no email address on the line. It needs one, inside angle brackets, so "
               "the sign-off identifies a person")
    elif not name:
        why = "your name needs to come before the address, in front of the `<`"
    else:
        why = "the line is close but does not parse. It has to read exactly `Name <address>`"
    return why, fixed


def check_message(message):
    """Return (ok, why, fixed). `why` and `fixed` are None when ok, or when nothing was attempted."""
    lines = message.splitlines()
    if any(VALID.match(l.rstrip("\r")) for l in lines):
        return True, None, None
    for l in lines:
        if NEARISH.match(l) and l.strip():
            why, fixed = _diagnose(l)
            return False, why, fixed
    return False, None, None


def _report(failures, base):
    """Print the contributor-facing explanation. Every branch here is read by a stranger."""
    near = [f for f in failures if f[1]]
    absent = [f for f in failures if not f[1]]

    for sha, why, fixed, subject in failures:
        print("::error::{} {}".format(sha[:9], why or "has no Signed-off-by line"))

    if near:
        print("")
        print("You DID sign off. The line is there and the format is wrong, which is a much")
        print("smaller problem than this check's red cross makes it look.")
        for sha, why, fixed, subject in near:
            print("")
            print("  commit {}  {}".format(sha[:9], subject))
            print("  what is wrong: {}".format(why))
            print("  make it read:  {}".format(fixed))
    if absent:
        print("")
        print("These commits carry no Signed-off-by line at all:")
        for sha, why, fixed, subject in absent:
            print("  commit {}  {}".format(sha[:9], subject))

    print("")
    print("EVERY commit in a pull request needs its own sign-off, so pushing one more")
    print("commit on top will not clear this gate. The existing commit has to carry it.")
    print("")
    print("From a terminal, this rewrites them all with the line in place:")
    print("    git rebase --signoff {}".format(base or "<the base commit>"))
    print("    git push --force-with-lease")
    print("")
    print("If you edited in the browser with the pencil icon, the shortest route is:")
    print("  1. In your fork, delete the branch behind this pull request.")
    print("  2. Edit the file again. Put the sign-off in the Extended description box")
    print("     when you commit, not in the title.")
    print("  3. Open a new pull request. All 8 checks will run on it.")
    print("")
    print("A maintainer cannot add this for you: it certifies that you wrote the change")
    print("and have the right to submit it, so us typing it would defeat the point. If")
    print("any of the above is unclear, say so in a comment and we will walk you through")
    print("it. We would much rather do that than lose your work, and we have lost work")
    print("to this exact check before.")


def _git(args):
    return subprocess.run(["git"] + args, capture_output=True, text=True, check=True).stdout


def run_range(rng):
    base = rng.split("..")[0] if ".." in rng else None
    try:
        shas = [s for s in _git(["rev-list", rng]).split() if s]
    except subprocess.CalledProcessError as e:
        sys.exit("could not list commits in {}: {}".format(rng, e.stderr.strip()[:200]))
    if not shas:
        print("No commits in {}, so there is nothing to check.".format(rng))
        return 0
    failures = []
    for sha in shas:
        message = _git(["log", "-1", "--format=%B", sha])
        subject = message.splitlines()[0] if message.strip() else ""
        ok, why, fixed = check_message(message)
        if not ok:
            failures.append((sha, why, fixed, subject))
    if failures:
        _report(failures, base)
        return 1
    print("All {} commit(s) signed off.".format(len(shas)))
    return 0


CASES = [
    # (message, expected_ok, substring expected in the reason)
    ("t\n\nSigned-off-by: A Name <a@b.com>", True, None),
    ("t\n\nsigned-off-by: A Name <a@b.com>", True, None),
    ("t\n\nSigned-off-by:   A Name   <a@b.com>   ", True, None),
    ("t\n\nSigned-off-by: A Name <a@b.com>\nSigned-off-by: B <c@d.io>", True, None),
    # The real PR #15 message. This is the regression test for the whole file.
    ("Fixed spelling mistake in helloworld.html\n\n"
     "Signed-off-by: Sanika Rangayyan (sanika.rangayyan@gmail.com)", False, "angle brackets"),
    ("t\n\nSigned-off-by: A Name [a@b.com]", False, "angle brackets"),
    ("t\n\nSigned-off-by: A Name a@b.com", False, "angle brackets"),
    ("t\n\nSigned-off-by: A Name <a@b.com", False, "angle bracket"),
    ("t\n\nSigned-off-by: A Name", False, "no email address"),
    ("t\n\nSigned-off-by: <a@b.com>", False, "name needs to come before"),
    ("t\n\n  Signed-off-by: A Name <a@b.com>", False, "start of the line"),
    ("t\n\nSigned off by: A Name <a@b.com>", False, "exactly `Signed-off-by:`"),
    ("t\n\nnothing here", False, None),
    ("", False, None),
]


def self_test():
    bad = 0
    for message, want_ok, want_sub in CASES:
        ok, why, fixed = check_message(message)
        label = (message.splitlines() or [""])[-1][:48]
        if ok != want_ok:
            print("FAIL  ok={} want={}  {!r}".format(ok, want_ok, label))
            bad += 1
            continue
        if want_sub and (not why or want_sub not in why):
            print("FAIL  reason {!r} lacks {!r}  ({})".format(why, want_sub, label))
            bad += 1
            continue
        if not want_ok and want_sub and fixed and "<" not in fixed:
            print("FAIL  corrected line is not corrected: {!r}".format(fixed))
            bad += 1
            continue
        print("ok    {:<5} {}".format(str(ok), label))
    if bad:
        print("\n{} case(s) failed. This is OUR bug, not a contributor's.".format(bad))
        return 1
    print("\n{} cases pass.".format(len(CASES)))
    return 0


def main():
    ap = argparse.ArgumentParser(description="Check DCO sign-offs and explain any failure.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--range", help="commit range, e.g. BASE..HEAD")
    g.add_argument("--message-file", help="a single commit message to check")
    g.add_argument("--self-test", action="store_true", help="check this script against known cases")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if args.message_file:
        with open(args.message_file, encoding="utf-8") as fh:
            message = fh.read()
        ok, why, fixed = check_message(message)
        if ok:
            print("Signed off.")
            return 0
        _report([("(stdin)", why, fixed, (message.splitlines() or [""])[0])], None)
        return 1
    return run_range(args.range)


if __name__ == "__main__":
    sys.exit(main())
