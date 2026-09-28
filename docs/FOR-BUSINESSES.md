# Connecting your food business to Shipley Farms

For restaurants, butchers, grocers, distributors, meal-kit companies, and other online meat
sellers who want to carry our beef and connect it to systems they already run.

This page is deliberately separate from the rest of this repository. Everything else here is
for people contributing code. This is for people who want to **buy**.

## Be clear about where we are

We would rather lose your time now than waste it later, so:

**What works today.** Our complete product list is public and free to read: names, cuts,
categories, descriptions, images, and retail prices, as a single file. You can display our
products on your site, in an app, on a menu board, or in a price checker with no account and no
key. See [`API.md`](API.md).

**What does not work yet.** There is no way to place an order programmatically, check stock, see
your own wholesale pricing, or track an order. No authentication exists. **The partner API is in
design, not in production.** Anyone who tells you otherwise has not read this page.

So today you can build something that shows our beef. Buying it still goes through a person.

## Buying from us, which does work

The commercial relationship comes first, and it is not a technical process:

1. **Apply for a wholesale account.** <https://shipleyfarmsbeef.com/wholesale-application?utm_source=github&utm_medium=repo&utm_campaign=shipley-integrations&utm_content=businesses>
2. **A person reviews it** and works out pricing, terms, delivery or shipping, and what we can
   reliably supply you. Those are set case by case and we do not publish them, so please do not
   expect to find a price list here.
3. Background on how we work is at <https://shipleyfarmsbeef.com/wholesale?utm_source=github&utm_medium=repo&utm_campaign=shipley-integrations&utm_content=businesses>.

Once you are an account, integration becomes a conversation we can actually have, because we
know who you are and what you buy.

## See what we are proposing

**[Try the partner API demo in your browser](https://healthymeats.github.io/shipley-integrations/demo/)**

It runs entirely on your machine against invented sample data. Sign in as a fictional restaurant, look at your pricing, place a standing order, watch it move through statuses, and read the invoices. Each screen shows the proposed HTTP request behind it.

Nothing in it is real and no price in it is a quote. It exists so you can disagree with a concrete thing rather than a paragraph.

## If you want to help shape the partner API

We are designing the authenticated API now. The planned scope is your own pricing, order
placement, order status, your invoices, and shipment tracking. Explicitly never in it: any other
customer's data, our costs, or anything touching payment processing.

**We would much rather build it around one real business than guess at a generic one.** If you
are a restaurant group, a distributor, or a store that would genuinely order this way, tell us:

- What system is on the other end (Toast, Square, Shopify, an ERP, something you wrote)
- What you actually need to do with it, in the order you would do it
- What currently takes your staff the most time when ordering from a supplier

[Open an issue tagged `partner-api`](../../issues/new/choose), or email
<gray@shipleyfarmsbeef.com>. If you would rather not discuss it in public, email is fine and we
will not post the details.

Being early here means the API gets designed around a workflow that already exists in your
kitchen or warehouse rather than one we imagined.

## What we will not do

- **Publish a wholesale price list.** Pricing is per-account. It is not a secret from you; it is
  just not something we put where every competitor can read it.
- **Connect anything directly to our production systems.** Every integration is reviewed and
  enabled by our team. That protects you as much as us.
- **Promise a delivery date for the partner API.** We are a farm. When we have something real
  you can use, it will appear here and we will tell the people who asked.

## Who to talk to

Commercial: <gray@shipleyfarmsbeef.com>, or the wholesale application above.
Technical: [an issue in this repository](../../issues).
Either way, a person reads it.
