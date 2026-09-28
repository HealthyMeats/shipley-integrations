# Shipley Farms Integrations

Open tools for building on top of [Shipley Farms](https://shipleyfarmsbeef.com), a family
cattle operation in Vilas, North Carolina.

We run our storefront on ERPNext and we would rather build it with other people than alone.
This repository is for **your** code: connectors, clients, and tools that talk to our catalog.
What you contribute here stays yours, under your name, under the MIT license.

**You do not need access to our internal code to build anything in here.** Our store's own
source is private, because it holds live payment configuration. Everything in this repository
works against public, documented data instead.

## Start here

| If you want to... | Go to |
|---|---|
| Read our product catalog | [`docs/API.md`](docs/API.md) |
| See working code | [`examples/`](examples/) |
| Publish an integration | [`integrations/`](integrations/) and [`CONTRIBUTING.md`](CONTRIBUTING.md) |
| Make your first contribution | [`site/helloworld.html`](site/helloworld.html), live at [/helloworld](https://shipleyfarmsbeef.com/helloworld) |
| Report a bug in our store | [Open an issue](../../issues/new/choose) |
| Report a security problem | [`SECURITY.md`](SECURITY.md), **not** a public issue |
| Talk to us without GitHub | <https://shipleyfarmsbeef.com/developers> |

## Never sent a pull request before?

Start at **<https://shipleyfarmsbeef.com/helloworld>**. There is exactly one deliberate spelling
mistake on that page, and [the file behind it](site/helloworld.html) is in this repository. Fix
it, open a pull request, and when we merge it the live page changes. No install, no setup, about
ten minutes.

That page is a real page on a working farm's storefront, not a sandbox. See [`site/`](site/).

## What is open

Today there is one stable, public surface: a schema.org product feed at
**<https://shipleyfarmsbeef.com/files/catalog.json>**. It covers 234 products with SKU, name,
URL, category, brand, description, image, and price. It is a static file, so reading it costs
us nothing and you can poll it as often as you like.

A scoped **partner API** for wholesale ordering (your prices, your orders, your invoices,
your tracking) is in design. If you supply restaurants, run one, or operate another store that
would buy from us, open an issue tagged `partner-api` and tell us what you need. We would
rather build it against a real integration than guess.

## What is not open, and why

- **Anyone else's data.** Customers, orders, contacts. Not now, not scoped, not aggregated.
- **Our margins, costs, and supplier terms.** We are a small operation competing with large
  ones. This is the one thing that would genuinely hurt us.
- **Anything touching payment processing.** Not because we are hiding it, but because there
  is no version of a community patch to a live card path that we could accept responsibly.

Everything else is a conversation. If you want something that is not listed, ask.

## Use the catalog file, not a crawler

`catalog.json` has everything the product pages have, in one request, already structured. It is
faster for you than scraping and it is the polite way to do this.

Automated scanning, load testing and bulk crawling are not welcome. If your project needs
something the catalog file does not cover, ask and we will find a way to give it to you
properly.

## License

MIT. See [`LICENSE`](LICENSE). Contributors keep their copyright and sign off with a DCO line
rather than assigning anything to us. See [`CONTRIBUTING.md`](CONTRIBUTING.md).
