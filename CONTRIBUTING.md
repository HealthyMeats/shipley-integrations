# Contributing

Anyone is welcome here. You do not need to be a professional developer, and you do not need
permission to start.

## The short version

1. Open an issue describing what you want to build or what you found.
2. For an integration, copy [`integrations/_template/`](integrations/_template/) and work there.
3. Sign off your commits (`git commit -s`). That is the whole legal process.
4. Open a pull request. We will get to it, and we will tell you either way.

## What we are looking for

**Integrations** that connect our catalog to something else: a restaurant ordering system, a
point of sale, a storefront platform, a menu board, an inventory tool. These live in
`integrations/<your-integration>/` and you own them.

**Examples** that show someone else how to do something in fewer steps than we managed.

**Bug reports about our live store.** These are genuinely valuable and they are not lesser
contributions. A clear description of what you did and what happened is worth more to us than
a patch we have to reverse engineer.

**Documentation fixes.** If `docs/API.md` is wrong or unclear, it is a bug.

## What we cannot take

- **Patches to our checkout, payment, or authentication code.** Our store's source is private
  and stays that way. There is no version of a community patch to a live card path that we
  could accept responsibly. This is not about trust; it is about who is accountable when a
  customer's payment fails at 9pm on a Saturday.
- **Dependencies we cannot audit.** Keep integrations light. If you need a large framework,
  say why in the issue first.
- **Anything requiring credentials to run in CI.** Tests must pass against fixture data.

If you believe you have found a bug in our internal code and you have a fix in mind, describe
it in an issue. Link a gist or your own fork rather than pasting code. We will take it from
there and credit you.

## Sign-off (DCO), not a CLA

We use the [Developer Certificate of Origin](https://developercertificate.org/). You keep your
copyright. You are just confirming you have the right to send us the code.

Add `-s` to your commit and git appends the line for you:

```bash
git commit -s -m "add square catalog sync"
```

That produces `Signed-off-by: Your Name <you@example.com>`. CI checks for it.

## Review standards

We read every pull request. We will be direct about what needs changing and we will tell you
plainly if something is not going to land, rather than letting it sit open for a month. We are
not going to quote you a turnaround time we cannot keep; this is a farm, and calving season
beats code review.

Integrations get reviewed for: does it work, is it safe to run, does it respect the rate
guidance in [`SECURITY.md`](SECURITY.md), and is it documented well enough that a stranger
could use it.

We do not require tests for an integration you own, but we will not debug one that has none.

## Not on GitHub?

Use <https://shipleyfarmsbeef.com/developers>. It reaches the same people.
