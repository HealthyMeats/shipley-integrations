#!/usr/bin/env python3
"""Block business-sensitive disclosure from reaching a public file.

This repository is public and one of its files is published verbatim as a live page. Candour
that is right in an internal document is wrong here. Two categories have already had to be
removed after the fact, which is why this is now a gate rather than a habit:

  1. An operational weakness, published on a page whose job is to attract people who write
     automated clients. It stated how much traffic it takes to stop the site and what that
     stops. That is a targeting guide.
  2. Internal quality gaps stated as counts, e.g. how many products lack a photo. That tells a
     competitor how finished the catalogue is.

The rule: never publish anything that helps someone size the business, book the business, find
a weakness, or identify a named individual who did not ask to be named.

Product names and prices are NOT covered: they are on the storefront and in the public catalog
file by design. This blocks aggregate figures ABOUT the business, not the goods it sells.

Run locally before a pull request:  python3 tools/validate_disclosure.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", "fixtures", "__pycache__", ".github"}
SKIP_FILES = {"validate_disclosure.py"}
EXTS = (".md", ".html", ".py", ".txt", ".yml", ".yaml", ".json")

# (pattern, what is wrong, what to do instead)
RULES = [
    (r"\b(hard )?daily (compute )?(limit|ceiling|cap)\b",
     "describes a capacity limit",
     "say the catalog file is the supported way to read the data, and stop there"),
    (r"\b(compute|cpu)[- ]?(ceiling|budget|limit|quota)\b",
     "describes a capacity limit", "as above"),
    (r"\b(small|modest|limited|cheap|tiny)\s+hosting\b",
     "describes our infrastructure as small",
     "do not characterise the infrastructure at all"),
    (r"(whole|entire)\s+(site|thing)\s+(stops|goes down|returns errors)",
     "describes a total-outage failure mode",
     "do not describe what breaks or how"),
    (r"register at the (counter|farm)|point of sale at the farm|takes? the register down",
     "names the blast radius of an outage",
     "do not connect the website to the store register in public"),
    (r"\bno (staging|test environment|automatic deploys?|auto[- ]deploys?)\b",
     "tells a reader there is no test gate before production",
     "say a team member reviews and publishes every change"),
    (r"\b\d[\d,]*\s+(of our\s+)?(products?|items?|SKUs?)\s+(have|has|lack|are missing|with)\s+no\b",
     "publishes an internal quality gap as a count",
     "describe the need without the number"),
    (r"\b(revenue|turnover|profit|margins?|COGS|cost of goods)\s+(of|was|is|are|were)\s*[\$\d]",
     "publishes a financial figure", "never publish financial figures"),
    (r"\$[\d,]+(\.\d+)?\s*(k|m|/mo|per month|a month|/yr|per year|a year|in (sales|revenue))",
     "publishes a financial figure", "never publish financial figures"),
    (r"\b\d[\d,]*\s+(customers?|orders?|wholesale accounts?|subscribers?|employees?|staff)\b",
     "publishes a business volume figure",
     "never publish counts of customers, orders, accounts or staff"),
    (r"\b(we only have|we can(no|')?t afford|we are struggling|barely)\b",
     "signals financial or operational weakness",
     "state the constraint neutrally or leave it out"),
    (r"\b\d+(\.\d+)?%\s+(of (our )?(sales|revenue|orders|customers|traffic))",
     "publishes a business ratio", "never publish business ratios"),
]


def files():
    for base, dirs, names in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for n in names:
            if n.endswith(EXTS) and n not in SKIP_FILES:
                yield os.path.join(base, n)


def main():
    findings = []
    checked = 0
    for path in sorted(files()):
        try:
            text = open(path, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        checked += 1
        for pattern, what, instead in RULES:
            for m in re.finditer(pattern, text, re.I):
                line = text[:m.start()].count("\n") + 1
                findings.append((os.path.relpath(path, ROOT), line, m.group(0).strip(),
                                 what, instead))
    print("  checked {} file(s)".format(checked))
    if not findings:
        print("  no business-sensitive disclosure found.")
        return 0
    print("\n{} problem(s):\n".format(len(findings)))
    for path, line, hit, what, instead in findings:
        print("  {}:{}".format(path, line))
        print("      found:   {!r}".format(hit[:70]))
        print("      problem: this {}".format(what))
        print("      instead: {}\n".format(instead))
    print("This repository is public and site/ files are published as live pages.")
    print("See tools/validate_disclosure.py for the rule.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
