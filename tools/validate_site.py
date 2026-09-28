#!/usr/bin/env python3
"""Validate site/*.html the same way the publisher does, so a contributor gets the verdict on
their pull request instead of after a maintainer tries to publish it.

These files are served from the same origin as a live checkout, so contributed markup is
untrusted input. This mirrors the gate in launch-automation/prod-queue/360_helloworld_page.py.
"""
import html.parser
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")

FORBIDDEN = [
    (re.compile(r"<\s*script", re.I), "a <script> tag"),
    (re.compile(r"<\s*iframe", re.I), "an <iframe>"),
    (re.compile(r"<\s*object|<\s*embed", re.I), "an <object> or <embed>"),
    (re.compile(r"\son[a-z]+\s*=", re.I), "an inline event handler (onclick=, onload=, ...)"),
    (re.compile(r"javascript\s*:", re.I), "a javascript: URL"),
    (re.compile(r"<\s*form", re.I), "a <form> tag"),
    (re.compile(r"<\s*link|<\s*style", re.I), "a <link> or <style> tag"),
]
ALLOWED_HOSTS = ("shipleyfarmsbeef.com", "github.com", "healthymeats.github.io")
REQUIRED = {
    "helloworld.html": [
        ("exactly one spelling mistake", "the first-task invitation"),
        ("site/helloworld.html", "the link to the editable source file"),
        ("Automated scanning and load testing are not welcome", "the automated-traffic notice"),
        ("gray@shipleyfarmsbeef.com", "the security contact"),
        ("SHIPLEY_HELLOWORLD_V1", "the publisher marker"),
    ],
}
VOID = {"br", "hr", "img", "meta", "input", "link", "source", "area", "base", "col", "wbr"}


class Balance(html.parser.HTMLParser):
    def __init__(self):
        html.parser.HTMLParser.__init__(self)
        self.stack, self.bad = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        elif tag in self.stack:
            self.bad.append(tag)


def check(filename):
    errs = []
    path = os.path.join(SITE, filename)
    with open(path, encoding="utf-8") as fh:
        markup = fh.read()

    for pattern, what in FORBIDDEN:
        m = pattern.search(markup)
        if m:
            errs.append("{}:{}: {} is not allowed here".format(
                filename, markup[:m.start()].count("\n") + 1, what))

    for url in re.findall(r'(?:src|href)="(https?://[^"]+)"', markup):
        if not any(h in url for h in ALLOWED_HOSTS):
            errs.append("{}: off-site reference {!r}. Allowed: {}".format(
                filename, url[:70], ", ".join(ALLOWED_HOSTS)))

    for needle, what in REQUIRED.get(filename, []):
        if needle not in markup:
            errs.append("{}: {} is missing (looked for {!r}). Please do not remove it.".format(
                filename, what, needle))

    b = Balance()
    b.feed(markup)
    if b.stack:
        errs.append("{}: unclosed tag(s): {}".format(filename, ", ".join(b.stack[:5])))
    if b.bad:
        errs.append("{}: mismatched closing tag(s): {}".format(filename, ", ".join(b.bad[:5])))

    if "—" in markup:
        errs.append("{}: contains an em dash. House style uses plain punctuation.".format(filename))

    heads = [int(h) for h in re.findall(r"<h([1-6])", markup, re.I)]
    for prev, nxt in zip(heads, heads[1:]):
        if nxt > prev + 1:
            errs.append("{}: heading level jumps from h{} to h{}. Screen readers navigate by "
                        "these.".format(filename, prev, nxt))
            break
    return errs


def main():
    if not os.path.isdir(SITE):
        print("no site/ directory")
        return 0
    names = sorted(f for f in os.listdir(SITE) if f.endswith(".html"))
    if not names:
        print("no site/*.html to check")
        return 0
    errs = []
    for n in names:
        found = check(n)
        print("  {:<28} {}".format(n, "OK" if not found else "FAILED"))
        errs += found
    if errs:
        print("\n{} problem(s):".format(len(errs)))
        for e in errs:
            print("  * " + e)
        print("\nThese pages are live on a working storefront. See site/README.md.")
        return 1
    print("\n{} page(s) validated.".format(len(names)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
