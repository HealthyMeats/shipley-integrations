#!/usr/bin/env python3
"""Validate every integrations/*/integration.json. Run by CI and safe to run locally."""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTEGRATIONS = os.path.join(ROOT, "integrations")
REQUIRED = ("name", "summary", "maintainer", "status", "language", "uses", "license")
STATUSES = ("working", "experimental", "unmaintained")
KNOWN_SURFACES = ("catalog.json", "llms.txt", "sitemap.xml", "partner-api")
SECRET = re.compile(r"(sk_live_|rk_live_|pk_live_|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY)")


def check(dirname):
    errs = []
    path = os.path.join(INTEGRATIONS, dirname)
    manifest = os.path.join(path, "integration.json")
    if not os.path.exists(manifest):
        return ["{}: no integration.json".format(dirname)]
    if not os.path.exists(os.path.join(path, "README.md")):
        errs.append("{}: no README.md".format(dirname))
    try:
        m = json.load(open(manifest))
    except ValueError as e:
        return ["{}: integration.json is not valid JSON ({})".format(dirname, e)]

    for key in REQUIRED:
        if not m.get(key):
            errs.append("{}: missing required field {!r}".format(dirname, key))
    if m.get("name") and m["name"] != dirname:
        errs.append("{}: name {!r} does not match the directory".format(dirname, m["name"]))
    if m.get("status") and m["status"] not in STATUSES:
        errs.append("{}: status {!r} must be one of {}".format(
            dirname, m["status"], ", ".join(STATUSES)))
    contact = (m.get("maintainer") or {}).get("contact")
    if not contact:
        errs.append("{}: maintainer.contact is required so users can reach you".format(dirname))
    for surface in m.get("uses") or []:
        if surface not in KNOWN_SURFACES:
            errs.append("{}: unknown surface {!r}. Known: {}".format(
                dirname, surface, ", ".join(KNOWN_SURFACES)))

    # Never let a live key reach a public repository, even in a fixture.
    for base, _dirs, files in os.walk(path):
        for fn in files:
            fp = os.path.join(base, fn)
            try:
                text = open(fp, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            if SECRET.search(text):
                errs.append("{}: what looks like a live credential in {}".format(
                    dirname, os.path.relpath(fp, ROOT)))
    return errs


def main():
    if not os.path.isdir(INTEGRATIONS):
        print("no integrations/ directory")
        return 0
    names = sorted(d for d in os.listdir(INTEGRATIONS)
                   if os.path.isdir(os.path.join(INTEGRATIONS, d)))
    errs = []
    for n in names:
        found = check(n)
        print("  {:<28} {}".format(n, "OK" if not found else "FAILED"))
        errs += found
    if errs:
        print("\n{} problem(s):".format(len(errs)))
        for e in errs:
            print("  * " + e)
        return 1
    print("\n{} integration(s) validated.".format(len(names)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
