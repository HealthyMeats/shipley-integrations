# Integrations

One directory per integration. **You own yours.** Put your name in `integration.json`, keep
your copyright, and change it without asking us.

```
integrations/
  square-catalog-sync/
    integration.json      required, see below
    README.md             required: what it does, how to run it
    ...your code...
```

## Getting started

```bash
cp -r integrations/_template integrations/my-integration
```

Then edit `integration.json` and `README.md`, and open a pull request. CI validates the
manifest, so you will know within a minute if something is missing.

## `integration.json`

```json
{
  "name": "square-catalog-sync",
  "summary": "Mirrors the Shipley Farms catalog into a Square item library.",
  "maintainer": { "name": "Your Name", "contact": "you@example.com" },
  "status": "working",
  "language": "python",
  "uses": ["catalog.json"],
  "license": "MIT"
}
```

| Field | Values |
|---|---|
| `name` | Must match the directory name. Lowercase, hyphens |
| `status` | `working`, `experimental`, or `unmaintained` |
| `uses` | Which Shipley surfaces it touches. `catalog.json` today |
| `maintainer.contact` | How a user reaches you. An address or a profile URL |

`status: unmaintained` is a respectable answer, not a failure. Setting it honestly is more
useful to the next person than letting them find out the hard way.

## House rules

- **Cache.** Do not re-fetch `catalog.json` on every request. See
  [`examples/catalog_client.py`](../examples/catalog_client.py).
- **Identify yourself** in a `User-Agent`.
- **Label catch weight prices as estimates.** Items flagged `x_shipley_catch_weight` are sold
  by the pound and the listed price is not the final charge. See [`docs/API.md`](../docs/API.md).
- **No secrets in the repository.** Not yours, not ours, not in a test fixture.
- **Tests run offline.** Use `fixtures/catalog.sample.json`. CI has no network credentials and
  never will.
