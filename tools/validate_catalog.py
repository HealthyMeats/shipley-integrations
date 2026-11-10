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
least one warning), and 2 when the file could not be read at all.

Standard library only. The schema checker below supports just the JSON Schema keywords
catalog.schema.json uses, and --self-test fails if the schema starts using another one.
"""
import argparse
import collections
import copy
import datetime
import json
import os
import re
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


def _resolve(schema, root):
    while "$ref" in schema:
        node = root
        for part in schema["$ref"].lstrip("#/").split("/"):
            node = node[part]
        schema = node
    return schema


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
        elif "pattern" in schema and not re.search(schema["pattern"], value):
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


# ----------------------------------------------------------------------------- plain words

def _show(value):
    text = json.dumps(value, ensure_ascii=False)
    return text if len(text) <= 60 else text[:57] + "..."


def _product_label(item, index):
    if isinstance(item, dict) and isinstance(item.get("sku"), str) and item["sku"].strip():
        if isinstance(item.get("name"), str) and item["name"].strip():
            return 'Product {} "{}"'.format(item["sku"], item["name"])
        return "Product {}".format(item["sku"])
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


def _price(item):
    offer = item.get("offers")
    price = offer.get("price") if isinstance(offer, dict) else None
    return price if _is_type(price, "number") and price > 0 else None


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
                    sku, len(items), ", ".join(_show(i.get("name")) for i in items))))

    for _i, item in products:
        if "offers" not in item and not item.get("x_shipley_note"):
            findings.append(Finding(PROBLEM, "no-price", (
                "{} has no price, and no note saying why. Only variant templates (products "
                "where you pick a size or style on the product page) should be without a price, "
                "and those carry a note (x_shipley_note) explaining it.").format(label[id(item)])))

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
            owner = 'another product, {} "{}"'.format(stem, names[stem])
        else:
            owner = "a different product code, {}".format(stem)
        shared = [u for u in users[image] if u is not item]
        also = ""
        if shared:
            also = " The same picture is also used by {}.".format(
                ", ".join(u.get("sku", "?") for u in shared))
        findings.append(Finding(WARNING, "image-other-product", (
            "{} uses the picture {}, which is named after {}, so it may show a different "
            "cut.{}").format(label[id(item)], filename, owner, also)))
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
                    label[id(item)], match.group(1))))
    return findings


def _category_findings(products, label):
    by_category = collections.defaultdict(list)
    for _i, item in products:
        if isinstance(item.get("category"), str) and item["category"].strip():
            by_category[item["category"]].append(item)
    return [Finding(WARNING, "lonely-category", (
        'The category "{}" has only one product, {}. It may be a misspelt category name, or a '
        "product filed in the wrong place.").format(category, label[id(items[0])]))
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
                    label[id(item)], _price_words(item, price), how, category, typical)))
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
        return []  # the schema already reports a malformed time
    age = (today - made_on).days
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
        # utf-8-sig also reads a file saved with a byte order mark, as some editors do.
        with open(path, encoding="utf-8-sig") as fh:
            return json.load(fh)
    except FileNotFoundError:
        _cannot_check("Could not find the file {}. Check the path, or leave out --file to check "
                      "the sample in fixtures/.".format(path))
    except json.JSONDecodeError as e:
        _cannot_check("The file {} is not valid JSON, the format the catalog is written in, so "
                      "it cannot be checked. The first mistake is on line {}, column {}: "
                      "{}.".format(path, e.lineno, e.colno, e.msg))


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
]


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
    if bad:
        print("\n{} case(s) failed.".format(bad))
        return 1
    print("\n{} cases pass.".format(len(CASES) + 2))
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

    if args.self_test:
        return self_test()
    with open(SCHEMA_PATH, encoding="utf-8") as fh:
        schema = json.load(fh)
    catalog = load(args.file)
    today = args.today or datetime.datetime.now(datetime.timezone.utc).date()
    findings = check(catalog, schema, today, args.max_age_days)
    return report(findings, args.file, catalog, args.strict)


if __name__ == "__main__":
    sys.exit(main())
