#!/usr/bin/env python3
"""Check that the PUBLISHED /helloworld carries the seed the ledger names.

WHY THIS EXISTS SEPARATELY FROM validate_seed.py. That gate reads the repository, and its
`--require-live` flag means "live in the repository file". It makes no network request. So on
2026-10-02 a fix merged, seed 3 was planted, `main` went green, and the published page went on
serving seed 2 for a day: the typo a contributor had already fixed and been credited for. The
next person to arrive would have fixed `catagory` again and found their diff already in main.

validate_seed.py's own docstring promises a red build "instead of a page that quietly invites
people to find a typo that is no longer there". That is exactly the state it could not see,
because the page it describes is not the file it reads. This script reads the page.

WHAT COUNTS AS A FAILURE, AND WHAT DOES NOT. A mismatch is a failure: the page is reachable, and
it does not carry the current seed, which means the publisher owes a run. An outage is NOT a
failure by default. The farm's storefront going down should not turn this repository red for
people who cannot do anything about either problem, so an unreachable page prints COULD NOT
VERIFY and exits 0. Pass --strict to invert that, which is the right mode for a monitor.

WHY THIS IS NOT A PULL REQUEST GATE. A publish debt belongs to a maintainer. Failing an outside
contribution over it would block the one thing this repository is asking for, and the contributor
could not fix it if they tried.

The seed is a SHA-256 hash in site/SEEDED.md, so this verifies without printing the answer.

    python3 tools/validate_live_seed.py
    python3 tools/validate_live_seed.py --strict
    python3 tools/validate_live_seed.py --url http://127.0.0.1:8000/helloworld
"""
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate_seed import _Prose, matches, read_ledger  # noqa: E402

# The apex, never www and never the v.frappe.cloud host: both 308-redirect.
DEFAULT_URL = "https://shipleyfarmsbeef.com/helloworld"

# Identifies these requests so they can be told apart from real readers. The hourly run shows up
# in the farm's Web Page View rows, and a page-view count for /helloworld that silently includes
# our own monitoring is a worse problem than the one this script solves.
USER_AGENT = ("shipley-integrations-live-seed-gate/1 "
              "(+https://github.com/HealthyMeats/shipley-integrations)")

ATTEMPTS = 3
BACKOFF = 3
TIMEOUT = 20

PUBLISH_HINT = ("  cd <shipley-farms> && git -C shipley-integrations pull --ff-only origin main\n"
                "  PROD_CONFIRM=1 SITE_URL=https://shipleyfarmsbeef.com \\\n"
                "      python3 launch-automation/prod-queue/360_helloworld_page.py --apply")


def fetch(url):
    """Return (html, None) or (None, reason). Retries, because a blip is not a mismatch."""
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    })
    reason = "no attempt made"
    for attempt in range(1, ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                if response.status != 200:
                    reason = "HTTP {}".format(response.status)
                else:
                    return response.read().decode("utf-8", "replace"), None
        except urllib.error.HTTPError as exc:
            reason = "HTTP {}".format(exc.code)
        except Exception as exc:
            reason = "{}: {}".format(type(exc).__name__, exc)
        if attempt < ATTEMPTS:
            time.sleep(BACKOFF * attempt)
    return None, reason


def main():
    argv = sys.argv[1:]
    strict = "--strict" in argv
    url = DEFAULT_URL
    if "--url" in argv:
        index = argv.index("--url")
        if index + 1 >= len(argv):
            sys.exit("--url needs a value.")
        url = argv[index + 1]

    number, relpath, digest = read_ledger()

    body, reason = fetch(url)
    if body is None:
        print("  seed {:<3} COULD NOT VERIFY   {}".format(number, reason))
        if strict:
            print("\n--strict was passed, so an unverifiable page is a failure.")
            return 1
        print("\nThe page was unreachable after {} attempts, which says nothing about whether the\n"
              "seed is published. Not failing on it: a storefront outage is not this repository's\n"
              "build breaking. Re-run once {} answers.".format(ATTEMPTS, url))
        return 0

    parser = _Prose()
    parser.feed(body)
    found = matches(parser.text(), digest)

    if not found:
        print("  seed {:<3} NOT ON THE LIVE PAGE   {}".format(number, url))
        print("\nsite/SEEDED.md names seed {} and {} contains it, but the published page does not.\n"
              "Whatever the live page is inviting people to find, it is not the current seed, and\n"
              "the likely answer is a seed somebody already fixed. Publish the page:\n\n{}\n\n"
              "The publisher reads the local clone, so pull before you apply or it republishes\n"
              "the same stale bytes.".format(number, relpath, PUBLISH_HINT))
        return 1

    print("  seed {:<3} published at {:<48} OK".format(number, url))
    return 0


if __name__ == "__main__":
    sys.exit(main())
