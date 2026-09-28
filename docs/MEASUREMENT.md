# Measuring what this repository sends to the farm

Internal note, kept public because it explains the tracking parameters on our own links and
nobody should have to guess why they are there.

## What the links carry

Every prose link from this repository to shipleyfarmsbeef.com carries:

```
?utm_source=github&utm_medium=repo&utm_campaign=shipley-integrations&utm_content=<file>
```

`utm_content` names the document the click came from (`readme`, `projects`, `educators`,
`agents`, `api-docs`, ...), so Google Analytics shows which page persuaded someone, not just
that GitHub sent them.

`tools/validate_links.py` enforces this in CI, and enforces the three cases where tags must
**not** appear: inside code examples, on documented API endpoints, and anywhere in `site/*.html`
(those files are published as pages on the farm's own site, so their links are internal).

## Why tags rather than relying on the referrer

GitHub sends `Referrer-Policy: no-referrer-when-downgrade`, so an HTTPS click does pass the full
referring URL today. Analytics would record `github.com` as a referral either way.

The tags are worth it anyway, for three reasons: they survive a future change to GitHub's
referrer policy, they distinguish which document sent the visitor, and they put the traffic in
the campaign reports where the rest of the farm's acquisition data lives instead of in an
undifferentiated referral bucket.

## In Google Analytics

Traffic acquisition, then Session source / medium. Look for **`github / repo`**. Break down by
Session campaign for `shipley-integrations`, and by `utm_content` to see which document works.

## What this will and will not capture

**Humans clicking a link: captured.** Ordinary browser, ordinary analytics.

**Agents and bots: mostly not captured, and no amount of configuration fixes that.** Analytics
runs in JavaScript. A script fetching a page, a crawler, or an agent reading the catalog file
never executes it and never appears. Anything measuring agent traffic has to be server side.

That is a real limitation and worth stating plainly rather than reporting a number that quietly
excludes most non-human traffic. Three practical consequences:

- A rise in `github / repo` sessions means **people**, which is usually the question worth asking.
- Agent interest shows up instead as requests for `/files/catalog.json`, which is a static file
  and leaves no analytics trace at all. Reading those counts requires the hosting provider's
  request log rather than Google Analytics.
- `AGENTS.md` asks agents to identify themselves in a `User-Agent` string, and the example
  client does. That is the only clean way to tell a well-behaved agent from a browser in a
  server log, and it depends on cooperation, so treat any count as a floor.

## A caution about search

GitHub marks every outbound link `rel="nofollow"`, verified 2026-09-28. Links from this
repository pass no ranking signal to the farm's site and never will. The value here is the
repository itself appearing in search results and sending real people, plus the farm's own pages
linking outward, not link equity flowing back. Do not let anyone sell this as backlink building.
