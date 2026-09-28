#!/usr/bin/env python3
"""Keep attribution working and keep examples copy-pasteable.

Four rules, each of which has already been broken once:

  1. A prose link from this repository to shipleyfarmsbeef.com MUST carry UTM parameters.
     Without them every visitor lands in Google Analytics as an undifferentiated "github.com
     referral" and nobody can tell whether any of this brings the farm traffic.
  2. A link inside a fenced code block MUST NOT carry them. Those are examples a developer
     copies, and tracking parameters there end up hardcoded in someone's client and teach the
     wrong canonical URL.
  3. Files in site/ MUST NOT carry them at all. Those files are published as pages ON the farm
     site, so their links are internal; tagging them would attribute the farm's own traffic to
     GitHub and corrupt the numbers this is meant to produce.
  4. Documented API endpoints stay clean, for the same reason as rule 2.

Run before a pull request:  python3 tools/validate_links.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = "https://shipleyfarmsbeef.com"
UTM = "utm_source=github"
REQUIRED = ["utm_source=github", "utm_medium=repo", "utm_campaign=shipley-integrations",
            "utm_content="]
KEEP_CLEAN = ("/files/catalog.json", "/files/sitemap-products.xml", "/sitemap.xml",
              "/llms.txt", "/agents.md", "/robots.txt", "/files/status.json",
              "/files/status.html")
URL = re.compile(re.escape(HOST) + r'[^\s\)\]"\'<>`]*')


def lines_with_context(text):
    """Yield (lineno, line, in_code_block)."""
    in_block = False
    for i, line in enumerate(text.split("\n"), 1):
        if line.lstrip().startswith("```"):
            in_block = not in_block
            continue
        yield i, line, in_block or line.startswith("    ")


def check(relpath, text):
    errs = []
    # Only site/*.html is PUBLISHED as a live page. site/README.md is repository
    # documentation that happens to live in that folder, and its links are outbound.
    in_site = (relpath.replace(os.sep, "/").startswith("site/")
               and relpath.endswith(".html"))
    for lineno, line, in_code in lines_with_context(text):
        for m in URL.finditer(line):
            url = m.group(0).rstrip(".,;:*")
            tagged = UTM in url
            clean_endpoint = any(k in url for k in KEEP_CLEAN)
            where = "{}:{}".format(relpath, lineno)
            if in_site:
                if tagged:
                    errs.append((where, url, "site/ files are published ON the farm site, so "
                                             "this is an internal link and must not be tagged"))
                continue
            if in_code and tagged:
                errs.append((where, url, "inside a code block: this is an example someone will "
                                         "copy, so it must not carry tracking parameters"))
            elif not in_code and not tagged and not clean_endpoint:
                errs.append((where, url, "prose link with no UTM: this visit would land in "
                                         "analytics as an untraceable github.com referral"))
            elif not in_code and tagged:
                missing = [r for r in REQUIRED if r not in url]
                if missing:
                    errs.append((where, url, "incomplete UTM, missing: " + ", ".join(missing)))
            elif clean_endpoint and tagged:
                errs.append((where, url, "documented API endpoint must stay clean"))
    return errs


def main():
    errs, checked = [], 0
    for base, dirs, names in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "fixtures"}]
        for n in names:
            if not n.endswith((".md", ".html")):
                continue
            path = os.path.join(base, n)
            rel = os.path.relpath(path, ROOT)
            try:
                text = open(path, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            checked += 1
            errs += check(rel, text)
    print("  checked {} file(s)".format(checked))
    if not errs:
        print("  every farm link is attributed correctly.")
        return 0
    print("\n{} problem(s):\n".format(len(errs)))
    for where, url, why in errs:
        print("  {}".format(where))
        print("      {}".format(url[:96]))
        print("      {}\n".format(why))
    print("Prose links need: ?utm_source=github&utm_medium=repo"
          "&utm_campaign=shipley-integrations&utm_content=<this-file>")
    return 1


if __name__ == "__main__":
    sys.exit(main())
