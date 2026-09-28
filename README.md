# Shipley Farms Integrations

Open tools for building on top of [Shipley Farms](https://shipleyfarmsbeef.com/?utm_source=github&utm_medium=repo&utm_campaign=shipley-integrations&utm_content=readme), a family
cattle operation in Vilas, North Carolina.

We run our storefront on ERPNext and we would rather build it with other people than alone.
This repository is for **your** code: connectors, clients, and tools that talk to our catalog.
What you contribute here stays yours, under your name, under the MIT license.

**You do not need access to our internal code to build anything in here.** Our store's own
source is private, because it holds live payment configuration. Everything in this repository
works against public, documented data instead.

## What this is today, and what it is not

Read this before you build anything.

| | Status |
|---|---|
| Read our full product list, with retail prices | **Works now.** One public file, no key |
| Display our products in your own site, menu or app | **Works now** |
| See wholesale pricing for your business | **Not available.** Pricing is per-account and never public |
| Check stock, pack sizes, lead times, minimums | **Not available yet** |
| Place an order, or check an order's status | **Not available yet.** There is no ordering endpoint |
| Authenticate as a partner | **Not available yet** |

So: you can build something that **shows** our beef. You cannot yet build something that
**buys** it. The authenticated partner API that would change that is in design, and we would
rather design it around a real business than guess. You can **[try the proposed design in your browser](https://healthymeats.github.io/shipley-integrations/demo/)** and tell us where it is wrong, and if you sell food for a living see [`docs/FOR-BUSINESSES.md`](docs/FOR-BUSINESSES.md).

One more thing worth knowing up front: the catalog file is a **periodic snapshot**, regenerated
by hand rather than live. Read `x_shipley_provenance.generated_at_utc` and treat the prices as
indicative, not as a quote.

## Start here

| If you want to... | Go to |
|---|---|
| Read our product catalog | [`docs/API.md`](docs/API.md) |
| See working code | [`examples/`](examples/) |
| Publish an integration | [`integrations/`](integrations/) and [`CONTRIBUTING.md`](CONTRIBUTING.md) |
| Make your first contribution | [`site/helloworld.html`](site/helloworld.html), live at [/helloworld](https://shipleyfarmsbeef.com/helloworld?utm_source=github&utm_medium=repo&utm_campaign=shipley-integrations&utm_content=readme) |
| Report a bug in our store | [Open an issue](../../issues/new/choose) |
| Report a security problem | [`SECURITY.md`](SECURITY.md), **not** a public issue |
| Find a project to build | [`docs/PROJECTS.md`](docs/PROJECTS.md) |
| Use this with a class | [`docs/FOR-EDUCATORS.md`](docs/FOR-EDUCATORS.md) |
| Check this cannot break the farm | [`docs/HOW-IT-STAYS-SEPARATE.md`](docs/HOW-IT-STAYS-SEPARATE.md) |
| Contribute as an AI agent | [`AGENTS.md`](AGENTS.md) |
| **See the partner API working** | **[Interactive demo](https://healthymeats.github.io/shipley-integrations/demo/)** |
| Connect your food business to us | [`docs/FOR-BUSINESSES.md`](docs/FOR-BUSINESSES.md) |
| Talk to us without GitHub | <https://shipleyfarmsbeef.com/helloworld?utm_source=github&utm_medium=repo&utm_campaign=shipley-integrations&utm_content=readme> |

## Never sent a pull request before?

Start at **<https://shipleyfarmsbeef.com/helloworld?utm_source=github&utm_medium=repo&utm_campaign=shipley-integrations&utm_content=readme>**. There is exactly one deliberate spelling
mistake on that page, and [the file behind it](site/helloworld.html) is in this repository. Fix
it, open a pull request, and when we merge it the live page changes. No install, no setup, about
ten minutes.

That page is a real page on a working farm's storefront, not a sandbox. See [`site/`](site/).

## Students, classes and interns

**Contributions here are citable.** A merged pull request is public and permanent, your name
goes in [`CONTRIBUTORS.md`](CONTRIBUTORS.md), and if someone asks us to confirm you contributed,
we will. See what we will and will not say about your work in that file.

Twenty project briefs at three difficulty levels, including analysis and design work for
security and IT courses, are in [`docs/PROJECTS.md`](docs/PROJECTS.md). Instructors, start at
[`docs/FOR-EDUCATORS.md`](docs/FOR-EDUCATORS.md).

Nothing you do here can reach our live systems, which is deliberate and is explained in
[`docs/HOW-IT-STAYS-SEPARATE.md`](docs/HOW-IT-STAYS-SEPARATE.md).

## What is open

Today there is one stable, public surface: a schema.org product feed at
**<https://shipleyfarmsbeef.com/files/catalog.json>**. Every product, with SKU, name, URL,
category, brand, description, image, and price. It is a static file, so reading it costs us
nothing and you can poll it as often as you like.

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
