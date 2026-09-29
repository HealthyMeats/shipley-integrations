#!/usr/bin/env python3
"""Validate site/*.html the way the publisher does, so a contributor gets the verdict on their
pull request instead of after a maintainer tries to publish it.

These files are served from the same origin as a live checkout, so contributed markup is
untrusted input. The rules are in `tools/sitegate.py`; read that file if a refusal here is not
self-explanatory, because it says why each rule exists rather than just what it forbids.

    python3 tools/validate_site.py

Every file in site/ is checked. Some of them also have to keep specific text: /helloworld
invites you to fix a deliberate typo, and a pull request that fixed the typo but deleted the
invitation would quietly close the door behind itself.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sitegate  # noqa: E402  (path has to be set before this import)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")

# filename -> (substring, what it is) that must survive any edit.
REQUIRED = {
    "helloworld.html": [
        ("exactly one spelling mistake", "the first-task invitation"),
        ("site/helloworld.html", "the link to the editable source file"),
        ("Automated scanning and load testing are not welcome", "the automated-traffic notice"),
        ("gray@shipleyfarmsbeef.com", "the security contact"),
        ("SHIPLEY_HELLOWORLD_V1", "the publisher marker"),
    ],
    "directory.template.html": [
        ("SHIPLEY_DIRECTORY_V1", "the publisher marker"),
        ("<!-- GENERATED_SECTIONS -->", "the placeholder the page's lists are rendered into"),
    ],
}


def main():
    if not os.path.isdir(SITE):
        print("no site/ directory, nothing to validate")
        return 0

    names = sorted(f for f in os.listdir(SITE) if f.endswith(".html"))
    if not names:
        # Not a pass. These files ARE live pages; if they have all gone, say so loudly rather
        # than reporting success on an empty set.
        print("site/ contains no .html files. Two live pages are published from here, so this")
        print("is either a mistake or a deletion that needs to be deliberate.")
        return 1

    problems = []
    for name in names:
        with open(os.path.join(SITE, name), encoding="utf-8") as fh:
            markup = fh.read()
        found = sitegate.check(markup, name, required=REQUIRED.get(name, []))
        print("  {:<28} {}".format(name, "OK" if not found else "FAILED"))
        problems += found

    if problems:
        print("\n{} problem(s):\n".format(len(problems)))
        for p in problems:
            print("  * " + p)
        print("\nThese pages are live on a working storefront that takes real orders, and they")
        print("share an origin with its checkout. See site/README.md and tools/sitegate.py.")
        print("If you think a rule is wrong, open an issue: several of them were relaxed")
        print("because somebody asked.")
        return 1

    print("\n{} page(s) validated.".format(len(names)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
