# Shipley Farms public data

Last reviewed 2026-09-28.

There is exactly one stable public surface today. This document describes it honestly,
including what it will not do for you.

## The catalog feed

```
GET https://shipleyfarmsbeef.com/files/catalog.json
```

No authentication. No key. No rate limit. It is a static file, so reading it costs us nothing
and you can fetch it as often as you find useful.

It is a [schema.org](https://schema.org) `ItemList` of `Product` objects. Read
`numberOfItems` rather than hardcoding a count; the catalog changes.

### A product record

```json
{
  "@type": "Product",
  "sku": "SS1231",
  "name": "Signature Huston Ribeye",
  "url": "https://shipleyfarmsbeef.com/products/ss1231",
  "category": "Dry-Aged Steaks",
  "brand": { "@type": "Brand", "name": "Shipley Farms" },
  "description": "Our signature steak. Well-marbled and full of flavor.",
  "image": "https://shipleyfarmsbeef.com/files/SS1231.png",
  "offers": {
    "@type": "Offer",
    "url": "https://shipleyfarmsbeef.com/products/ss1231",
    "priceCurrency": "USD",
    "price": 60.3,
    "description": "Sold by the pound. This price is an estimate based on average weight..."
  },
  "x_shipley_catch_weight": true
}
```

| Field | Always present | Notes |
|---|---|---|
| `sku` | yes | Our stable identifier. Use this as your key, not `name` |
| `name` | yes | Display name. Changes for marketing reasons; do not key on it |
| `url` | yes | Canonical product page. Absolute |
| `category` | yes | For example `Dry-Aged Steaks`, `Ground Beef` |
| `brand` | yes | Always Shipley Farms |
| `description` | yes | |
| `image` | yes | Absolute. Served at up to 768px; our uploader downscales |
| `offers.price` | yes | USD. **Read the catch weight section below before you show this** |
| `x_shipley_catch_weight` | no | Present and `true` on catch weight items |
| `x_shipley_note` | no | Free text when an item needs a caveat |

### Catch weight: the one thing to get right

Some items are sold **by the pound**, and beef does not come in exact pounds. For those
items `offers.price` is an **estimate based on average weight**, and the customer's final
charge is the actual weight packed, which may be higher or lower.

If you display our prices, say so. A menu board or storefront that shows `$60.30` as a firm
price for a catch weight item is showing your customer a number we cannot honour.

```python
price = item["offers"]["price"]
if item.get("x_shipley_catch_weight"):
    label = "about ${:.2f}".format(price)   # estimate, final charge is by actual weight
else:
    label = "${:.2f}".format(price)         # firm
```

### Freshness: this is a snapshot, not a live endpoint

The file carries its own provenance block:

```json
"x_shipley_provenance": {
  "generated_at_utc": "2026-09-26T00:59:05Z",
  "snapshot": true,
  "freshness_warning": "Prices, product availability, and the product list itself change."
}
```

**Read `generated_at_utc` and act on it.** We regenerate after price changes, but there is no
guarantee of how recent any given copy is. If your integration quotes a price to a paying
customer, link through to `url` for the live figure, or warn when the snapshot is stale:

```python
import datetime
gen = catalog["x_shipley_provenance"]["generated_at_utc"]
age = datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(gen)
if age.days > 14:
    ...  # treat prices as indicative only
```

### Availability

`availability` appears **only** on items explicitly on backorder. Its absence means unknown,
not in stock. Do not build a stock display on this field. If you need real availability, that
is a partner API conversation.

## What is deliberately not documented here

Our store exposes other endpoints that its own pages call. They are not documented, not
supported, not stable, and we ask you not to build on them. They change without notice and
anything you build on them will break.

Use `catalog.json`. If it does not do what you need, open an issue and say so, and we will
look at documenting a supported way to get it.

## The partner API, in design

A scoped, authenticated API for partners who buy from us. Planned surface:

- Your price list, scoped to your account
- Order placement and order status
- Your invoices and payment terms
- Shipment tracking and delivery windows

Explicitly never in it: anyone else's data, our costs or margins, and anything touching
payment processing.

If you are a restaurant, a distributor, or a store that would buy from us, open an issue
tagged `partner-api` describing what system you are on and what you need to do. We would much
rather design this against a real integration than guess at one.

## Other public files

| URL | What it is |
|---|---|
| `/llms.txt` | Site summary for AI assistants |
| `/agents.md` | What we ask automated agents to do and not do |
| `/sitemap.xml` | Standard sitemap |
| `/robots.txt` | Crawl rules. **Please honour them** |

## Questions

Open an issue, or use <https://shipleyfarmsbeef.com/developers> if you would rather not use
GitHub.
