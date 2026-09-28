# Partner API demo

An interactive demonstration of the ordering API we are designing for restaurants,
distributors and resellers.

**It is a demonstration, not a system.** There is no server, no account, no key, and no network
call. It runs entirely in the browser against `data.js`.

## Everything here is invented

Product names and SKUs are real and already public in our catalog file. **Every price is made
up**, deliberately round, and not derived from any real price, so no pricing or discount
structure can be inferred from it. Nothing shown is a quote.

## Why it exists

Nobody can react to an API described in prose. This makes the proposed design concrete enough
to argue with, which is the point: we would rather change it now, while changing it is free.

Each screen has a **"Show the API call behind this screen"** panel with the proposed request and
response. Those panels are the specification, kept next to the interface so the two cannot drift
apart while we are still designing.

## Run it

Any static server works, because it is three files and no build step:

```bash
python3 -m http.server 8790 --directory demo
```

Then open <http://localhost:8790>.

## Telling us it is wrong

That is what it is for. If you order beef for a living and a screen here does not match how you
actually work, [open an issue](../../issues/new/choose) or email gray@shipleyfarmsbeef.com. A
description of your real ordering process is worth more to us than a feature request.
