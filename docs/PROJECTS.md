# Project briefs

Things worth building, sized so you can tell whether you are done.

Everything here works against **public, static data**: the catalog file or the fixtures in
[`fixtures/`](../fixtures/). Nothing requires an account, a key, or any access to farm systems,
and **nothing here involves sending traffic at our live site.** See
[`HOW-IT-STAYS-SEPARATE.md`](HOW-IT-STAYS-SEPARATE.md).

Before starting anything past the starter tier, [open an issue](../../issues) saying which brief
and roughly when. Two people building the same thing is a waste of somebody's weekend.

**Every brief that displays a price must handle catch weight correctly.** Items flagged
`x_shipley_catch_weight` are sold by the pound and the listed price is an estimate. Showing one
as firm means showing a customer a number we cannot honour. This is the domain trap, it is
documented in [`API.md`](API.md), and getting it wrong is the most common way a submission
fails review.

---

## Starter: a few hours

### S1. Fix the deliberate typo
There is exactly one misspelling on <https://shipleyfarmsbeef.com/helloworld>, planted on
purpose. Find it, fix [`site/helloworld.html`](../site/helloworld.html), open a pull request.
**Done when:** merged. That is your name in [`CONTRIBUTORS.md`](../CONTRIBUTORS.md).

### S2. Printable price list
Read the catalog, produce a clean one-page printable price list grouped by category.
**Why it matters:** our staff currently have no good way to print one.
**Done when:** it prints legibly on one sheet, catch weight prices are marked as estimates, and
it regenerates from the live file rather than hardcoding anything.

### S3. Price-per-pound comparison
Not every cut is priced per pound in a way a shopper can compare at a glance.
**Done when:** a sortable table shows comparable value across cuts, and says plainly where a
comparison is not meaningful rather than inventing one.

### S4. Catalog schema validator
Write a validator that checks the catalog against a JSON Schema you define and reports
anomalies: missing images, absent prices, categories with one item, suspicious values.
**Why it matters:** we would run this. **Good first security project.**
**Done when:** it runs offline against the fixture, exits non-zero on a problem, and explains
each finding in a sentence a non-programmer understands.

### S5. Cut chart
Map our SKUs onto a diagram of a steer, so someone can click a region and see what we sell
from it. **Done when:** every beef SKU in the catalog maps to a region or is explicitly listed
as unmapped.

---

## Project: one to two weeks

### P1. A client library in another language
[`examples/catalog_client.py`](../examples/catalog_client.py) is Python. Write the equivalent in
JavaScript, Go, Rust, or C#. **Done when:** it caches, identifies itself, handles catch weight,
warns on a stale snapshot, has no dependencies beyond the standard library, and a stranger can
run it from your README.

### P2. New product notifier
A bot that watches the catalog and posts to Discord, Slack, or Matrix when something appears or
disappears. **Done when:** it survives a restart without re-announcing everything, and it polls
at a sensible interval rather than hammering.

### P3. Kitchen menu board
A display for a restaurant or kitchen showing current cuts and prices, readable across a room.
**Done when:** it works on a cheap screen, degrades gracefully when offline, and marks catch
weight prices as estimates.

### P4. Recipe to cuts
Give it a recipe, get the cuts to order. **Done when:** it handles a recipe naming something we
do not sell by saying so, rather than guessing at the nearest match.

### P5. Bulk share tracker
Someone who buys a quarter or a half gets a freezer full of labelled packages. Build them
something to track what they have left. **Done when:** a non-technical person can use it on a
phone without an account.

### P6. Accessibility audit
Review our public pages against WCAG 2.2 AA. Reading pages in a browser is fine; automated
scanning is not. **Deliverable is a document**, not code: what fails, which criterion, how bad,
how to fix. **Why it matters:** we care about this and we know we have gaps.
**Done when:** every finding names the specific success criterion and is reproducible from your
description.

---

## Capstone: a semester

### C1. Point of sale catalog sync
Sync our catalog into Square or Toast so a restaurant kitchen can order without retyping
anything. **Done when:** it handles updates and removals, not just the first import, and it
never silently overwrites something a user changed on their side.

### C2. Storefront bridge
Let another shop resell our products through Shopify or WooCommerce, pulling product data
automatically. **Done when:** the reseller can map our categories to theirs, and catch weight
is carried through rather than flattened into a fixed price.

### C3. Standing order tool
A restaurant that buys the same thing every week should not rebuild the order every week.
Design and build the ordering side, against fixtures. **Done when:** it models a repeating order
with substitutions and skips, and it is honest about what still needs a human.

### C4. Cost per plate
A chef pricing a menu needs to know what a dish costs them. Combine our cuts with yields and
portion sizes. **Done when:** a chef could actually use it, and it shows its working rather than
just a number.

---

## Security and IT: analysis and design

These need no access to anything and produce documents or offline tools. **None of them involve
touching our live systems.** They are real work: we would use the output.

### X1. Threat model for a public partner API
We are designing an authenticated API for restaurants and resellers (see [`API.md`](API.md)).
Threat model it before it exists. **Deliverable:** a document identifying assets, actors, trust
boundaries, and the attacks that matter, with proposed mitigations ranked by cost.
**Done when:** a working engineer could use it as a design input.

### X2. Authentication and authorisation specification
Given that partners must see their own pricing and orders and never anyone else's, specify the
model. Compare approaches, pick one, justify it, and describe what goes wrong under each failure
mode. **Done when:** it addresses key rotation, revocation, and what happens when a partner's
credential leaks.

### X3. Supply chain analysis
Our example client deliberately has zero dependencies. Take a realistic alternative
implementation that uses a dependency tree, and analyse what trusting it actually means: how
many transitive packages, how many maintainers, what a compromise would reach.
**Done when:** it argues a position rather than just counting packages.

### X4. Input validation and fuzzing harness
Build a harness that feeds malformed and hostile catalog data to a client (yours or ours) and
reports how it fails. Runs entirely offline against generated input.
**Done when:** it finds at least one real crash or misbehaviour and explains the root cause.

### X5. Harden the example client
Take [`examples/catalog_client.py`](../examples/catalog_client.py) and make it production grade:
timeouts, retries with backoff, response size limits, schema validation, safe cache handling.
**Done when:** each change is justified against a specific failure it prevents, and the code
stays readable enough for a beginner to learn from.

---

## Proposing your own

Please do. [Open an issue](../../issues) describing what you want to build and what data you
would need. The answer is usually yes, and when it is no we will tell you why rather than
letting it sit.
