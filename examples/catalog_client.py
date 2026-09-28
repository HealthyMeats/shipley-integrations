#!/usr/bin/env python3
"""A complete, dependency-free Shipley Farms catalog client.

Shows the three things every integration has to get right: cache instead of re-fetching,
respect the freshness warning, and label catch weight prices honestly.

    python3 catalog_client.py                      # fetch and summarise
    python3 catalog_client.py --category "Ground Beef"
    python3 catalog_client.py --sku SS1231
    python3 catalog_client.py --file ../fixtures/catalog.sample.json   # offline

Standard library only, on purpose: an integration you can read in one sitting is one you can
trust. MIT licensed, same as the rest of this repository.
"""
import argparse
import datetime
import json
import os
import sys
import urllib.request

CATALOG_URL = "https://shipleyfarmsbeef.com/files/catalog.json"
STALE_AFTER_DAYS = 14
CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".catalog_cache.json")


def load(url=CATALOG_URL, path=None, use_cache=True):
    """Return the parsed catalog. Prefers a local file, then a cache, then the network.

    The cache is not an optimisation, it is courtesy: a polite client does not re-fetch what it
    already has. The catalog is a periodic snapshot, so a one hour cache loses you nothing.
    """
    if path:
        with open(path) as fh:
            return json.load(fh)
    if use_cache and os.path.exists(CACHE_PATH):
        age = datetime.datetime.now().timestamp() - os.path.getmtime(CACHE_PATH)
        if age < 3600:
            with open(CACHE_PATH) as fh:
                return json.load(fh)
    req = urllib.request.Request(url, headers={
        # Identify yourself. It costs nothing and it means they can tell you apart from a bot.
        "User-Agent": "shipley-catalog-client/1.0 (+https://github.com/HealthyMeats/shipley-integrations)"
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    try:
        with open(CACHE_PATH, "w") as fh:
            json.dump(data, fh)
    except OSError:
        pass
    return data


def products(catalog):
    """Flatten the schema.org ItemList into plain Product dicts."""
    return [e["item"] for e in catalog.get("itemListElement", []) if e.get("item")]


def snapshot_age(catalog):
    """Days since the feed was generated, or None if the provenance block is missing."""
    gen = (catalog.get("x_shipley_provenance") or {}).get("generated_at_utc")
    if not gen:
        return None
    stamp = datetime.datetime.fromisoformat(gen.replace("Z", "+00:00"))
    return (datetime.datetime.now(datetime.timezone.utc) - stamp).days


def price_label(item):
    """Format a price the way Shipley Farms can actually honour it.

    Catch weight items are sold by the pound. The listed price is an estimate from average
    weight and the real charge is the weight packed. Showing it as firm misleads your customer.
    """
    offer = item.get("offers") or {}
    price = offer.get("price")
    if price is None:
        return "price on request"
    if item.get("x_shipley_catch_weight"):
        return "about ${:.2f} (by weight)".format(price)
    return "${:.2f}".format(price)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--file", help="read a local catalog.json instead of fetching")
    ap.add_argument("--category", help="show only this category")
    ap.add_argument("--sku", help="show one product in full")
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args(argv)

    catalog = load(path=args.file, use_cache=not args.no_cache)
    items = products(catalog)

    age = snapshot_age(catalog)
    if age is None:
        print("WARNING: no provenance block. Treat these prices as indicative only.\n")
    elif age > STALE_AFTER_DAYS:
        print("WARNING: this snapshot is {} days old. Check the product page before quoting "
              "a price to a customer.\n".format(age))
    else:
        print("Catalog generated {} day(s) ago, {} products.\n".format(age, len(items)))

    if args.sku:
        hit = [i for i in items if i.get("sku", "").upper() == args.sku.upper()]
        if not hit:
            print("No product with SKU {!r}.".format(args.sku))
            return 1
        print(json.dumps(hit[0], indent=2))
        return 0

    if args.category:
        items = [i for i in items if i.get("category") == args.category]
        if not items:
            cats = sorted({i.get("category", "") for i in products(catalog)})
            print("No category {!r}. Known categories:\n  {}".format(
                args.category, "\n  ".join(c for c in cats if c)))
            return 1

    by_cat = {}
    for i in items:
        by_cat.setdefault(i.get("category") or "Uncategorised", []).append(i)
    catch = 0
    for cat in sorted(by_cat):
        print(cat)
        for i in sorted(by_cat[cat], key=lambda x: x.get("name") or ""):
            catch += bool(i.get("x_shipley_catch_weight"))
            print("  {:<10} {:<44} {}".format(
                i.get("sku", "?"), (i.get("name") or "")[:44], price_label(i)))
        print()
    print("{} product(s), {} sold by weight (prices shown are estimates).".format(
        len(items), catch))
    return 0


if __name__ == "__main__":
    sys.exit(main())
