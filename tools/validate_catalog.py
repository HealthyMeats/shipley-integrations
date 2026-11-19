#!/usr/bin/env python3
"""Check a catalog file against tools/catalog.schema.json and explain every finding in plain words.

Brief S4 in docs/PROJECTS.md. It reads a local copy of the catalog, never the network, and
reports two kinds of finding:

- PROBLEMS break integrations: a product with no product code, no price and no note saying
  why, a price of zero, the wrong currency, a duplicated product code, a product count that does
  not match the list. Any problem makes the script exit with status 1.
- WARNINGS are worth a person's look, but integrations still work: a missing picture, a picture
  named after a different product, a stray number at the start of a description, a category
  with a single product, a price far from the rest of its category, a sold-by-weight price not
  marked as an estimate, a stale snapshot. They exit 0, unless --strict is given.

Missing pictures and descriptions are warnings rather than problems because the published
catalog has many of them, as docs/API.md says. A check that fails on every real run would soon
be ignored.

Each sentence is written for someone who does not program: what is wrong, then why it matters.
The schema's titles and descriptions supply the wording for schema findings, so a new rule in
the schema comes with its own explanation.

    python3 tools/validate_catalog.py                          # the fixture
    python3 tools/validate_catalog.py --file ~/catalog.json    # a copy you downloaded
    python3 tools/validate_catalog.py --strict                 # warnings fail too
    python3 tools/validate_catalog.py --self-test

Exit status: 0 when there are no problems, 1 when there is at least one (or, with --strict, at
least one warning), 2 when the file could not be read at all, and 3 when the tool itself or its
schema file is broken (a bug for the maintainers, never a fault in your file).

Standard library only. The schema checker below supports just the JSON Schema keywords
catalog.schema.json uses, and --self-test fails if the schema starts using another one.

Hardening (maintainers, 2026-11-18): every piece of text that comes from the catalog is shown
with control and invisible formatting characters escaped, so a tampered file cannot rewrite the
terminal or a CI log; files over MAX_BYTES, deeply nested JSON, directories and non-UTF-8 files
are refused with a plain message instead of a traceback; the schema is checked for unknown
keywords, unknown types, unresolvable or looping $refs and patterns that do not compile before
anything is validated against it.
"""
import argparse
import collections
import contextlib
import copy
import datetime
import functools
import io
import json
import math
import os
import stat
import re
import tempfile
import unicodedata
import statistics
import sys
import textwrap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(ROOT, "tools", "catalog.schema.json")
FIXTURE_PATH = os.path.join(ROOT, "fixtures", "catalog.sample.json")
STALE_AFTER_DAYS = 14  # the threshold docs/API.md and examples/catalog_client.py use
# A price more than this many times above or below its category's median looks like a typo.
PRICE_SPREAD = 3
# Product codes look like SS1231 or SS9B33. A picture file named like one belongs to that product.
SKU_LIKE = re.compile(r"^[A-Z]{2}[0-9A-Z]{4}$")
# "~12 Our signature steak" or "12-18 Flavorful cut", but not "10-12 oz Classic NY Strip".
STRAY_NUMBER = re.compile(
    r"^(~?\d+(?:\s*(?:-|to)\s*\d+)?)\s+(?!(?:oz|ounces?|lbs?|pounds?|g|kg)\b)", re.IGNORECASE)

# The published catalog is a few hundred kilobytes. Anything this large is not a catalog.
MAX_BYTES = 20 * 1024 * 1024

PROBLEM, WARNING = "problem", "warning"
Finding = collections.namedtuple("Finding", "severity code message")

SUPPORTED_KEYWORDS = {
    "$schema", "$id", "$defs", "$ref", "title", "description",
    "type", "const", "required", "properties", "items",
    "minLength", "pattern", "minimum", "exclusiveMinimum",
}
TYPE_WORDS = {
    "object": "a group of named fields",
    "array": "a list",
    "string": "text",
    "integer": "a whole number",
    "number": "a number",
    "boolean": "true or false",
}


# ---------------------------------------------------------------------------- schema checking

def _is_type(value, name):
    if isinstance(value, bool):  # JSON true/false is not a number, though Python says it is
        return name == "boolean"
    if name == "integer":
        return isinstance(value, int)
    if name == "number":
        return isinstance(value, (int, float))
    return isinstance(value, {"object": dict, "array": list, "string": str, "boolean": bool}[name])


class SchemaError(Exception):
    """The schema file itself is broken. A maintainer's bug, reported with exit status 3."""


def _resolve(schema, root):
    """Follow local $refs ("#/a/b") to the node they name. Refuses anything else, and loops."""
    seen = set()
    while isinstance(schema, dict) and "$ref" in schema:
        ref = schema["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/"):
            raise SchemaError("$ref {!r} is not a local reference starting with #/".format(ref))
        if ref in seen:
            raise SchemaError("$ref {!r} refers back to itself".format(ref))
        seen.add(ref)
        node = root
        for part in ref[2:].split("/"):
            if not isinstance(node, dict) or part not in node:
                raise SchemaError("$ref {!r} points at nothing".format(ref))
            node = node[part]
        schema = node
    return schema


@functools.lru_cache(maxsize=None)
def _pattern(text):
    return re.compile(text)


def schema_violations(value, schema, root, path=()):
    """Yield (path, rule, kind, value) for each place `value` breaks `schema`.

    `rule` is the schema node that was broken; its title and description become the message.
    Once a value has the wrong type or constant, nothing inside it is checked, so one mistake is
    reported once.
    """
    schema = _resolve(schema, root)
    if "const" in schema and value != schema["const"]:
        yield path, schema, "const", value
        return
    if "type" in schema and not _is_type(value, schema["type"]):
        yield path, schema, "type", value
        return
    if isinstance(value, str):
        if len(value.strip()) < schema.get("minLength", 0):
            yield path, schema, "empty", value
        elif "pattern" in schema and not _pattern(schema["pattern"]).search(value):
            yield path, schema, "pattern", value
    if _is_type(value, "number"):
        too_low = ("minimum" in schema and value < schema["minimum"]) or (
            "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"])
        if too_low:
            yield path, schema, "low", value
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for key in schema.get("required", []):
            if value.get(key) is None:
                yield path + (key,), _resolve(properties.get(key, {}), root), "missing", None
        for key, sub in properties.items():
            if value.get(key) is not None:
                yield from schema_violations(value[key], sub, root, path + (key,))
    if isinstance(value, list) and "items" in schema:
        for index, entry in enumerate(value):
            yield from schema_violations(entry, schema["items"], root, path + (index,))


def unsupported_keywords(schema, where="schema"):
    """List the keywords in `schema` this script does not check, so none is silently ignored."""
    found = []
    if isinstance(schema, dict):
        for key, sub in schema.items():
            if key not in SUPPORTED_KEYWORDS:
                found.append("{}.{}".format(where, key))
            if key in ("properties", "$defs"):
                for name, child in sub.items():
                    found += unsupported_keywords(child, "{}.{}.{}".format(where, key, name))
            elif key == "items":
                found += unsupported_keywords(sub, where + ".items")
    return found


def schema_errors(schema):
    """Every reason `schema` cannot be trusted, as plain strings. Empty means it is sound.

    Checked before any catalog is validated, so a broken schema is reported as the tool's fault
    (exit 3) rather than producing confusing findings about the catalog.
    """
    errors = ["unsupported keyword " + k for k in unsupported_keywords(schema)]

    def walk(node, where):
        if not isinstance(node, dict):
            return
        if "type" in node and node["type"] not in TYPE_WORDS:
            errors.append("{}: unknown type {!r}".format(where, node["type"]))
        if "pattern" in node:
            try:
                _pattern(node["pattern"])
            except (re.error, TypeError) as e:
                errors.append("{}: pattern does not compile ({})".format(where, e))
        if "$ref" in node:
            try:
                _resolve(node, schema)
            except SchemaError as e:
                errors.append("{}: {}".format(where, e))
        for key in ("properties", "$defs"):
            for name, child in (node.get(key) or {}).items():
                walk(child, "{}.{}.{}".format(where, key, name))
        if "items" in node:
            walk(node["items"], where + ".items")

    if not isinstance(schema, dict):
        return ["the schema is not a JSON object"]
    walk(schema, "schema")
    return errors


# ----------------------------------------------------------------------------- plain words

def _safe(text):
    """`text` with control and invisible formatting characters written as \\uXXXX.

    Catalog text is printed to a terminal or a CI log. An escape sequence or a right-to-left
    override in a product name could recolour, hide or reorder the report, so every string that
    came from the catalog goes through here before it is shown. Ordinary letters, accents and
    punctuation are untouched.
    """
    text = str(text).replace("\\", "\\\\")  # so a literal "\u001b" in the catalog cannot pose as an escape
    return "".join("\\u{:04x}".format(ord(ch))
                   if unicodedata.category(ch) in ("Cc", "Cf", "Cs", "Zl", "Zp") else ch
                   for ch in text)


def _show(value):
    text = _safe(json.dumps(value, ensure_ascii=False))
    return text if len(text) <= 60 else text[:57] + "..."


def _product_label(item, index):
    if isinstance(item, dict) and isinstance(item.get("sku"), str) and item["sku"].strip():
        if isinstance(item.get("name"), str) and item["name"].strip():
            return 'Product {} "{}"'.format(_safe(item["sku"]), _safe(item["name"]))
        return "Product {}".format(_safe(item["sku"]))
    return "Product number {} in the list".format(index + 1)


def _subject(catalog, path):
    if len(path) >= 2 and path[0] == "itemListElement" and isinstance(path[1], int):
        entry = catalog["itemListElement"][path[1]]
        return _product_label(entry.get("item") if isinstance(entry, dict) else None, path[1])
    return "The catalog"


def _schema_message(catalog, path, rule, kind, value):
    who = _subject(catalog, path)
    title = rule.get("title") or (str(path[-1]) if path else "catalog")
    why = rule.get("description", "")
    if kind == "missing":
        text = "{} has no {}.".format(who, title)
    elif kind == "type":
        text = "{}: the {} should be {}, but it is {}.".format(
            who, title, TYPE_WORDS[rule["type"]], _show(value))
    elif kind == "const":
        text = "{}: the {} is {}, but it should be {}.".format(
            who, title, _show(value), _show(rule["const"]))
    elif kind == "empty":
        text = "{}: the {} is blank.".format(who, title)
    elif kind == "pattern":
        text = "{}: the {} is {}, which does not look right.".format(who, title, _show(value))
    else:
        text = "{}: the {} is {}, which is too low.".format(who, title, _show(value))
    return "{} {}".format(text, why).strip()


def _price_words(item, price):
    if item.get("x_shipley_catch_weight") is True:
        return "about ${:.2f} (sold by weight, so an estimate)".format(price)
    return "${:.2f}".format(price)


# ---------------------------------------------------------------------------------- checks

def _products(catalog):
    """(index, product) for each well-formed entry. Malformed ones are already schema findings."""
    entries = catalog.get("itemListElement")
    if not isinstance(entries, list):
        return []
    return [(i, e["item"]) for i, e in enumerate(entries)
            if isinstance(e, dict) and isinstance(e.get("item"), dict)]


# No real product costs this much. Above it a price is a data error, and formatting it as
# dollars would overflow.
PRICE_CEILING = 1e9


def _price(item):
    offer = item.get("offers")
    price = offer.get("price") if isinstance(offer, dict) else None
    ok = _is_type(price, "number") and _finite(price) and 0 < price <= PRICE_CEILING
    return price if ok else None


def _finite(number):
    """math.isfinite, except that it never overflows on a huge whole number (those are finite)."""
    return True if isinstance(number, int) else math.isfinite(number)


def check(catalog, schema, today, max_age_days=STALE_AFTER_DAYS):
    """Return every Finding for `catalog`, problems first."""
    findings = [Finding(PROBLEM, "schema", _schema_message(catalog, *v))
                for v in schema_violations(catalog, schema, schema)]
    if not isinstance(catalog, dict):
        return findings
    products = _products(catalog)
    label = {id(item): _product_label(item, i) for i, item in products}
    names = {item["sku"]: item.get("name") for _i, item in products
             if isinstance(item.get("sku"), str)}

    count, entries = catalog.get("numberOfItems"), catalog.get("itemListElement")
    if _is_type(count, "integer") and isinstance(entries, list) and count != len(entries):
        findings.append(Finding(PROBLEM, "count", (
            "The catalog says it holds {} products (numberOfItems), but its list has {}. "
            "Integrations that trust the count will miss products, or look for ones that are "
            "not there.").format(count, len(entries))))

    by_sku = collections.defaultdict(list)
    for _i, item in products:
        if isinstance(item.get("sku"), str) and item["sku"].strip():
            by_sku[item["sku"]].append(item)
    for sku, items in by_sku.items():
        if len(items) > 1:
            findings.append(Finding(PROBLEM, "duplicate-sku", (
                "The product code {} is used by {} products: {}. Product codes must be unique, "
                "or other systems will mix these products up.").format(
                    _safe(sku), len(items), ", ".join(_show(i.get("name")) for i in items))))

    for _i, item in products:
        if "offers" not in item and not item.get("x_shipley_note"):
            findings.append(Finding(PROBLEM, "no-price", (
                "{} has no price, and no note saying why. Only variant templates (products "
                "where you pick a size or style on the product page) should be without a price, "
                "and those carry a note (x_shipley_note) explaining it.").format(label[id(item)])))
        offer = item.get("offers")
        price = offer.get("price") if isinstance(offer, dict) else None
        if _is_type(price, "number") and not price < 0 and not (_finite(price) and price <= PRICE_CEILING):
            findings.append(Finding(PROBLEM, "absurd-price", (
                "{} has a price of {}, which cannot be a real price. Integrations would show it "
                "or fail on it.").format(label[id(item)], _show(price))))

    findings += _picture_findings(products, label, names)
    findings += _description_findings(products, label)
    findings += _category_findings(products, label)
    findings += _price_findings(products, label)
    findings += _freshness_findings(catalog, today, max_age_days)
    return sorted(findings, key=lambda f: f.severity != PROBLEM)


def _picture_findings(products, label, names):
    findings = []
    users = collections.defaultdict(list)
    for _i, item in products:
        if isinstance(item.get("image"), str):
            users[item["image"]].append(item)
    for _i, item in products:
        image = item.get("image")
        if image is None:
            findings.append(Finding(WARNING, "no-image", (
                "{} has no picture. Sites that show the catalog will show a blank space or a "
                "placeholder instead of the cut.").format(label[id(item)])))
            continue
        if not isinstance(image, str) or not isinstance(item.get("sku"), str):
            continue
        filename = image.rstrip("/").rsplit("/", 1)[-1]
        stem = filename.rsplit(".", 1)[0]
        if not SKU_LIKE.match(stem) or stem.upper() == item["sku"].upper():
            continue
        if stem in names:
            owner = 'another product, {} "{}"'.format(_safe(stem), _safe(names[stem]))
        else:
            owner = "a different product code, {}".format(_safe(stem))
        shared = [u for u in users[image] if u is not item]
        also = ""
        if shared:
            also = " The same picture is also used by {}.".format(
                ", ".join(_safe(u.get("sku", "?")) for u in shared))
        findings.append(Finding(WARNING, "image-other-product", (
            "{} uses the picture {}, which is named after {}, so it may show a different "
            "cut.{}").format(label[id(item)], _safe(filename), owner, also)))
    return findings


def _description_findings(products, label):
    findings = []
    for _i, item in products:
        text = item.get("description")
        if text is None or (isinstance(text, str) and not text.strip()):
            findings.append(Finding(WARNING, "no-description", (
                "{} has no description, so shoppers have only its name to go on.").format(
                    label[id(item)])))
            continue
        match = STRAY_NUMBER.match(text) if isinstance(text, str) else None
        if match:
            findings.append(Finding(WARNING, "stray-number", (
                '{}: its description starts with "{}", which looks like a leftover note '
                "(perhaps a weight or a count) rather than words meant for shoppers.").format(
                    label[id(item)], _safe(match.group(1)))))
    return findings


def _category_findings(products, label):
    by_category = collections.defaultdict(list)
    for _i, item in products:
        if isinstance(item.get("category"), str) and item["category"].strip():
            by_category[item["category"]].append(item)
    return [Finding(WARNING, "lonely-category", (
        'The category "{}" has only one product, {}. It may be a misspelt category name, or a '
        "product filed in the wrong place.").format(_safe(category), label[id(items[0])]))
        for category, items in by_category.items() if len(items) == 1]


def _price_findings(products, label):
    findings = []
    by_category = collections.defaultdict(list)
    for _i, item in products:
        if _price(item) is not None and isinstance(item.get("category"), str):
            by_category[item["category"]].append(item)
    for category, items in by_category.items():
        if len(items) < 3:  # too few prices to say what is typical
            continue
        typical = statistics.median(_price(i) for i in items)
        for item in items:
            price = _price(item)
            if price > typical * PRICE_SPREAD:
                how = "more than {} times".format(PRICE_SPREAD)
            elif price < typical / PRICE_SPREAD:
                how = "less than 1/{} of".format(PRICE_SPREAD)
            else:
                continue
            findings.append(Finding(WARNING, "odd-price", (
                "{} is priced at {}, {} the typical price in {} (${:.2f}). It could be a typo, "
                "such as a missing or extra digit or a misplaced decimal point.").format(
                    label[id(item)], _price_words(item, price), how, _safe(category), typical)))
    for _i, item in products:
        offer = item.get("offers")
        if item.get("x_shipley_catch_weight") is not True or not isinstance(offer, dict):
            continue
        note = offer.get("description")
        if not (isinstance(note, str) and "estimate" in note.lower()):
            findings.append(Finding(WARNING, "catch-weight-unlabelled", (
                "{} is sold by the pound, but its price details do not say the price is an "
                "estimate. Someone reading only this file could quote it as a firm price, which "
                "the farm cannot honour, because the final charge is the weight packed.").format(
                    label[id(item)])))
    return findings


def _freshness_findings(catalog, today, max_age_days):
    provenance = catalog.get("x_shipley_provenance")
    made = provenance.get("generated_at_utc") if isinstance(provenance, dict) else None
    if made is None:
        return [Finding(WARNING, "no-date", (
            "The catalog does not say when it was made (x_shipley_provenance.generated_at_utc), "
            "so nobody can tell how old its prices are."))]
    try:
        made_on = datetime.datetime.strptime(made, "%Y-%m-%dT%H:%M:%SZ").date()
    except (TypeError, ValueError):
        if isinstance(made, str) and _pattern(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T").match(made):
            # Shaped like a time, so the schema passed it, but the date does not exist.
            return [Finding(WARNING, "bad-date", (
                "The catalog says it was made at {}, which is not a real date, so nobody can tell "
                "how old its prices are.").format(_show(made)))]
        return []  # the schema already reports a malformed time
    age = (today - made_on).days
    if age < 0:
        return [Finding(WARNING, "future-date", (
            "The catalog says it was made on {}, which is {} day(s) in the future. The date is "
            "wrong, so nobody can tell how old its prices are.").format(made_on.isoformat(), -age))]
    if age <= max_age_days:
        return []
    return [Finding(WARNING, "stale", (
        "The catalog was made on {}, {} days ago. Prices and products change, so treat its "
        "prices as a rough guide and check the product page before quoting one.").format(
            made_on.isoformat(), age))]


# ------------------------------------------------------------------------------- reporting

def report(findings, path, catalog, strict):
    """Print the findings and return the exit status."""
    products = len(_products(catalog)) if isinstance(catalog, dict) else 0
    try:
        shown = os.path.relpath(path)
    except ValueError:  # on Windows, a file on another drive has no relative path
        shown = path
    print("Checked {}: {} products.\n".format(shown, products))
    problems = [f for f in findings if f.severity == PROBLEM]
    warnings = [f for f in findings if f.severity == WARNING]
    for group, heading in (
            (problems, "{} problem(s). These break integrations, so fix them first:"),
            (warnings, "{} warning(s). Worth a look, though integrations still work:")):
        if not group:
            continue
        print(heading.format(len(group)))
        for number, finding in enumerate(group, 1):
            print(textwrap.fill(finding.message, width=96, initial_indent="  {:>2}. ".format(number),
                                subsequent_indent="      "))
        print()
    failed = bool(problems) or (strict and bool(warnings))
    if not findings:
        print("No problems or warnings found.")
    print("Result: {} problem(s), {} warning(s){}. Exit status {}.".format(
        len(problems), len(warnings), " (--strict: warnings count as failures)" if strict else "",
        int(failed)))
    return int(failed)


class NotStandardJSON(ValueError):
    """NaN, Infinity or -Infinity: Python's json accepts them, standard JSON does not."""


def _no_constant(name):
    raise NotStandardJSON(name)


def _cannot_check(message):
    print(message, file=sys.stderr)
    sys.exit(2)


def load(path):
    """Return the parsed file, or exit with status 2 and a plain explanation."""
    if re.match(r"^[a-z][a-z0-9+.-]*://", path, re.IGNORECASE):
        _cannot_check("This tool only reads files on your computer, so it never sends traffic to "
                      "the farm's site. Save the catalog from your browser and pass the saved "
                      "file with --file.")
    try:
        if os.path.isdir(path):
            _cannot_check("{} is a folder, not a file. Pass the catalog file itself with "
                          "--file.".format(path))
        if not stat.S_ISREG(os.stat(path).st_mode):
            _cannot_check("{} is not an ordinary file (it may be a device or a pipe), so it was "
                          "not read.".format(path))
        # Read at most one byte past the limit: the size a file reports can be wrong, the read
        # cannot.
        with open(path, "rb") as fh:
            raw = fh.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            _cannot_check("The file {} is larger than any catalog (the limit is {:,} bytes), so it "
                          "was not read.".format(path, MAX_BYTES))
        # utf-8-sig also reads a file saved with a byte order mark, as some editors do.
        return json.loads(raw.decode("utf-8-sig"), parse_constant=_no_constant)
    except FileNotFoundError:
        _cannot_check("Could not find the file {}. Check the path, or leave out --file to check "
                      "the sample in fixtures/.".format(path))
    except PermissionError:
        _cannot_check("The file {} exists, but this account is not allowed to read it.".format(path))
    except UnicodeDecodeError:
        _cannot_check("The file {} is not text in UTF-8, the encoding the catalog is saved in, so "
                      "it cannot be checked. It may be a different kind of file.".format(path))
    except json.JSONDecodeError as e:
        _cannot_check("The file {} is not valid JSON, the format the catalog is written in, so "
                      "it cannot be checked. The first mistake is on line {}, column {}: "
                      "{}.".format(path, e.lineno, e.colno, e.msg))
    except NotStandardJSON as e:
        _cannot_check("The file {} contains {}, which is not a number in standard JSON, so it "
                      "cannot be checked.".format(path, e))
    except RecursionError:
        _cannot_check("The file {} is nested far too deeply to be a catalog, so it was not "
                      "read.".format(path))
    except ValueError as e:  # e.g. a number thousands of digits long (Python's int limit)
        _cannot_check("The file {} could not be read as a catalog: {}.".format(path, _safe(e)))
    except OSError as e:
        _cannot_check("The file {} could not be read: {}.".format(path, e.strerror or e))


# ------------------------------------------------------------------------------- self-test

TODAY = datetime.date(2026, 11, 1)


def _clean_catalog():
    """A small catalog that passes every check, for the self-test to break one way at a time."""
    def product(sku, name, price, catch_weight=False):
        offer = {"@type": "Offer", "url": "https://shipleyfarmsbeef.com/products/" + sku.lower(),
                 "priceCurrency": "USD", "price": price}
        item = {"@type": "Product", "sku": sku, "name": name,
                "url": "https://shipleyfarmsbeef.com/products/" + sku.lower(),
                "category": "Dry-Aged Steaks", "brand": {"@type": "Brand", "name": "Shipley Farms"},
                "description": "Dry-aged and cut to order.",
                "image": "https://shipleyfarmsbeef.com/files/{}.png".format(sku), "offers": offer}
        if catch_weight:
            item["x_shipley_catch_weight"] = True
            offer["description"] = "Sold by the pound. This price is an estimate."
        return item
    items = [product("SS1231", "Ribeye", 60.3, True), product("SS1430", "Flat Iron", 35.3),
             product("SS8032", "Strip Steak", 48.9)]
    return {"@context": "https://schema.org", "@type": "ItemList", "numberOfItems": len(items),
            "x_shipley_provenance": {"generated_at_utc": "2026-10-30T12:00:00Z"},
            "itemListElement": [{"@type": "ListItem", "position": n, "item": item}
                                for n, item in enumerate(items, 1)]}


def _item(catalog, n=0):
    return catalog["itemListElement"][n]["item"]


def _add_product(catalog, **fields):
    item = copy.deepcopy(_item(catalog))
    item.update(fields)
    catalog["itemListElement"].append({"@type": "ListItem", "position": 4, "item": item})
    catalog["numberOfItems"] += 1


def _delete(mapping, key):
    del mapping[key]


# (what the case does, how it breaks the clean catalog, the finding codes expected, and a phrase
# the message must contain)
CASES = [
    ("clean catalog", lambda c: None, [], None),
    ("no product code", lambda c: _delete(_item(c), "sku"), ["schema"], "has no product code"),
    ("price of zero", lambda c: _item(c)["offers"].update(price=0), ["schema"], "too low"),
    ("price as text", lambda c: _item(c)["offers"].update(price="60.30"), ["schema"],
     "should be a number"),
    ("price true", lambda c: _item(c)["offers"].update(price=True), ["schema"],
     "should be a number"),
    ("wrong currency", lambda c: _item(c)["offers"].update(priceCurrency="EUR"), ["schema"],
     "US dollars"),
    ("relative page address", lambda c: _item(c).update(url="/products/ss1231"), ["schema"],
     "starting with https://"),
    ("wrong brand", lambda c: _item(c)["brand"].update(name="Other Farm"), ["schema"],
     "Shipley Farms"),
    ("malformed time", lambda c: c["x_shipley_provenance"].update(generated_at_utc="last week"),
     ["schema"], "generation time"),
    ("not a catalog at all", lambda c: c.clear() or c.update({"@type": "Product"}),
     ["schema", "schema", "schema", "no-date"], "ItemList"),
    ("count does not match", lambda c: c.update(numberOfItems=4), ["count"], "holds 4 products"),
    ("duplicated product code", lambda c: _item(c, 1).update(
        sku="SS1231", image="https://shipleyfarmsbeef.com/files/SS1231.png"), ["duplicate-sku"],
     "must be unique"),
    ("no price, no note", lambda c: _delete(_item(c), "offers"), ["no-price"], "no price"),
    ("no price, variant template", lambda c: (_delete(_item(c), "offers"), _item(c).update(
        x_shipley_note="Choose a size on the product page.")), [], None),
    ("no picture", lambda c: _delete(_item(c), "image"), ["no-image"], "no picture"),
    ("picture named after another product", lambda c: _item(c).update(
        image="https://shipleyfarmsbeef.com/files/SS1430.png"), ["image-other-product"],
     'SS1430 "Flat Iron"'),
    ("picture not named after a code", lambda c: _item(c).update(
        image="https://shipleyfarmsbeef.com/files/ribeye-2.png"), [], None),
    ("no description", lambda c: _delete(_item(c), "description"), ["no-description"],
     "no description"),
    ("stray number", lambda c: _item(c).update(description="~12 Our signature steak."),
     ["stray-number"], '"~12"'),
    ("stray range", lambda c: _item(c).update(description="12-18 Flavorful cut."),
     ["stray-number"], '"12-18"'),
    ("weight with a unit", lambda c: _item(c).update(description="10-12 oz Classic NY Strip."),
     [], None),
    ("one-product category", lambda c: _add_product(c, sku="GB0001", name="Ground Beef",
                                                     category="Ground Beef",
                                                     image="https://shipleyfarmsbeef.com/files/GB0001.png"),
     ["lonely-category"], '"Ground Beef" has only one product'),
    ("price ten times too high", lambda c: _item(c, 1)["offers"].update(price=353.0),
     ["odd-price"], "more than 3 times"),
    ("odd price on a catch weight item", lambda c: _item(c)["offers"].update(price=603.0),
     ["odd-price"], "about $603.00"),
    ("catch weight without an estimate", lambda c: _delete(_item(c)["offers"], "description"),
     ["catch-weight-unlabelled"], "firm price"),
    ("no provenance", lambda c: _delete(c, "x_shipley_provenance"), ["no-date"],
     "how old its prices are"),
    ("stale snapshot", lambda c: c["x_shipley_provenance"].update(
        generated_at_utc="2026-09-26T00:59:05Z"), ["stale"], "36 days ago"),
    # Hardening, 2026-11-18.
    ("snapshot dated in the future", lambda c: c["x_shipley_provenance"].update(
        generated_at_utc="2026-12-25T00:00:00Z"), ["future-date"], "in the future"),
    ("terminal escape in a name", lambda c: (_item(c).update(name="Rib\u001b[2Jeye"),
                                            _delete(_item(c), "image")), ["no-image"], "\\u001b"),
    ("right-to-left override in a category", lambda c: _add_product(
        c, sku="GB0001", name="Ground Beef", category="Ground\u202eBeef",
        image="https://shipleyfarmsbeef.com/files/GB0001.png"), ["lonely-category"], "\\u202e"),
    ("an entry that is not a product", lambda c: (c["itemListElement"].append("oops"),
                                                  c.update(numberOfItems=4)), ["schema"], "list entry"),
    # Final review, 2026-11-18.
    ("a price too large to be real", lambda c: _item(c, 1)["offers"].update(price=10 ** 400),
     ["absurd-price"], "cannot be a real price"),
    ("infinity as a price", lambda c: _item(c, 1)["offers"].update(price=float("inf")),
     ["absurd-price"], "cannot be a real price"),
    ("a date that does not exist", lambda c: c["x_shipley_provenance"].update(
        generated_at_utc="2026-02-30T00:00:00Z"), ["bad-date"], "not a real date"),
    ("a lone surrogate in a name", lambda c: (_item(c).update(name="Rib\ud800eye"),
                                             _delete(_item(c), "image")), ["no-image"], "\\ud800"),
    ("a literal backslash-u in a name", lambda c: (_item(c).update(name="Rib\\u001beye"),
                                                  _delete(_item(c), "image")), ["no-image"], "Rib\\\\u001beye"),
]

# Raw control or invisible formatting characters must never reach a message.
_UNSAFE = re.compile("[\x00-\x1f\x7f-\x9f\u200b-\u200f\u202a-\u202e\u2060-\u2069\ufeff\ud800-\udfff]")


def _expect_exit(code, fn):
    """True when fn() exits with `code`. Its refusal message is swallowed, to keep the run quiet."""
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            fn()
    except SystemExit as e:
        return e.code == code
    return False


def _hardening_tests(schema):
    """(name, passed) for the protections that are not about catalog content."""
    results = [("the real schema is sound", schema_errors(schema) == [])]
    broken = {
        "a $ref that loops": {"$defs": {"a": {"$ref": "#/$defs/a"}}, "items": {"$ref": "#/$defs/a"}},
        "a $ref to another site": {"items": {"$ref": "https://example.com/schema.json"}},
        "a $ref to nothing": {"items": {"$ref": "#/$defs/missing"}},
        "an unknown type": {"type": "date"},
        "a pattern that does not compile": {"type": "string", "pattern": "("},
        "an unsupported keyword": {"type": "string", "format": "email"},
    }
    for what, bad in broken.items():
        results.append(("a broken schema is caught: " + what, bool(schema_errors(bad))))
    for what, value in (("a list", []), ("plain text", "catalog"), ("a number", 7)):
        try:
            check(value, schema, TODAY)
            results.append(("{} instead of a catalog does not crash".format(what), True))
        except Exception:  # noqa: BLE001 - the point is that nothing escapes
            results.append(("{} instead of a catalog does not crash".format(what), False))
    global MAX_BYTES
    with tempfile.TemporaryDirectory() as tmp:
        def write(name, data):
            path = os.path.join(tmp, name)
            with open(path, "wb") as fh:
                fh.write(data)
            return path
        # Balanced, so it is valid JSON and only the depth can be what refuses it.
        deep = write("deep.json", b"[" * 200000 + b"]" * 200000)
        latin = write("latin.json", b"\xff\xfe\x00{")
        nan = write("nan.json", b'{"price": NaN}')
        digits = write("digits.json", b'{"price": ' + b"9" * 5000 + b"}")
        results.append(("NaN is refused as not standard JSON", _expect_exit(2, lambda: load(nan))))
        results.append(("a number thousands of digits long is refused", _expect_exit(2, lambda: load(digits))))
        if hasattr(os, "mkfifo"):
            pipe = os.path.join(tmp, "pipe.json")
            os.mkfifo(pipe)
            results.append(("a pipe is refused without being read", _expect_exit(2, lambda: load(pipe))))
        big = write("big.json", b"{}" + b" " * 2048)
        saved, MAX_BYTES = MAX_BYTES, 1024
        try:
            results.append(("an oversized file is refused", _expect_exit(2, lambda: load(big))))
        finally:
            MAX_BYTES = saved
        results.append(("deeply nested JSON is refused", _expect_exit(2, lambda: load(deep))))
        results.append(("a file that is not UTF-8 is refused", _expect_exit(2, lambda: load(latin))))
        results.append(("a folder is refused", _expect_exit(2, lambda: load(tmp))))
        results.append(("a web address is refused", _expect_exit(
            2, lambda: load("https://shipleyfarmsbeef.com/files/catalog.json"))))
    return results


def self_test():
    with open(SCHEMA_PATH, encoding="utf-8") as fh:
        schema = json.load(fh)
    bad = 0
    unknown = unsupported_keywords(schema)
    if unknown:
        print("FAIL  the schema uses keywords this script does not check: {}".format(
            ", ".join(unknown)))
        bad += 1
    for name, breaks, want_codes, want_phrase in CASES:
        catalog = _clean_catalog()
        breaks(catalog)
        findings = check(catalog, schema, TODAY)
        leaked = [f.message for f in findings if _UNSAFE.search(f.message)]
        if leaked:
            print("FAIL  {}: a raw control character reached a message".format(name))
            bad += 1
            continue
        codes = sorted(f.code for f in findings)
        if codes != sorted(want_codes):
            print("FAIL  {}: found {}, wanted {}".format(name, codes, sorted(want_codes)))
            for f in findings:
                print("        " + f.message)
            bad += 1
            continue
        if want_phrase and not any(want_phrase in f.message for f in findings):
            print("FAIL  {}: no message mentions {!r}".format(name, want_phrase))
            for f in findings:
                print("        " + f.message)
            bad += 1
            continue
        print("ok    {}".format(name))
    with open(FIXTURE_PATH, encoding="utf-8") as fh:
        fixture = json.load(fh)
    problems = [f for f in check(fixture, schema, TODAY) if f.severity == PROBLEM]
    if problems:
        print("FAIL  the fixture has problems:")
        for f in problems:
            print("        " + f.message)
        bad += 1
    else:
        print("ok    the fixture has no problems")
    hardening = _hardening_tests(schema)
    for name, passed in hardening:
        print("{}  {}".format("ok  " if passed else "FAIL", name))
        bad += 0 if passed else 1
    if bad:
        print("\n{} case(s) failed.".format(bad))
        return 1
    print("\n{} cases pass.".format(len(CASES) + 2 + len(hardening)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--file", default=FIXTURE_PATH,
                    help="the catalog file to check (default: fixtures/catalog.sample.json)")
    ap.add_argument("--strict", action="store_true", help="exit 1 on warnings as well as problems")
    ap.add_argument("--max-age-days", type=int, default=STALE_AFTER_DAYS,
                    help="warn when the snapshot is older than this (default: %(default)s)")
    ap.add_argument("--today", type=datetime.date.fromisoformat,
                    help="the date to measure the snapshot's age from, as YYYY-MM-DD "
                         "(default: today, in UTC)")
    ap.add_argument("--self-test", action="store_true", help="check this script against known cases")
    args = ap.parse_args(argv)

    # A terminal that cannot show a character (Windows cp1252, say) gets an escape instead of a
    # crash halfway through the report.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError):
            pass
    if args.self_test:
        try:
            return self_test()
        except Exception as e:  # noqa: BLE001 - a broken self-test is the tool's fault, exit 3
            print("The self-test itself failed to run ({}: {}). This is a bug in the tool.".format(
                type(e).__name__, _safe(e)), file=sys.stderr)
            return 3
    if args.max_age_days < 0:
        ap.error("--max-age-days cannot be negative")
    schema = load_schema()
    catalog = load(args.file)
    today = args.today or datetime.datetime.now(datetime.timezone.utc).date()
    try:
        findings = check(catalog, schema, today, args.max_age_days)
    except Exception as e:  # a bug in this tool must never be mistaken for a clean catalog
        print("validate_catalog.py hit an internal error and could not finish ({}: {}). This is "
              "a bug in the tool, not a fault in your file; please report it.".format(
                  type(e).__name__, _safe(e)), file=sys.stderr)
        return 3
    return report(findings, args.file, catalog, args.strict)


def load_schema():
    """Read and vet catalog.schema.json, or exit 3: a broken schema is the tool's fault."""
    try:
        with open(SCHEMA_PATH, encoding="utf-8") as fh:
            schema = json.load(fh)
    except (OSError, ValueError) as e:
        print("The schema file {} could not be read ({}). This is a bug in the tool, not a fault "
              "in your file.".format(SCHEMA_PATH, e), file=sys.stderr)
        sys.exit(3)
    errors = schema_errors(schema)
    if errors:
        print("The schema file {} is broken, so nothing was checked. This is a bug in the tool, "
              "not a fault in your file:\n  {}".format(SCHEMA_PATH, "\n  ".join(errors)), file=sys.stderr)
        sys.exit(3)
    return schema


if __name__ == "__main__":
    sys.exit(main())
