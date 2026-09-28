# site/

**The files in here are live pages on <https://shipleyfarmsbeef.com/?utm_source=github&utm_medium=repo&utm_campaign=shipley-integrations&utm_content=site-readme>.**

This is the part most open source projects cannot offer you. A change you make here does not go
into a demo or a sandbox. When it is merged, it appears on a working farm's actual website, the
one customers buy beef from.

| File | Live at |
|---|---|
| `helloworld.html` | <https://shipleyfarmsbeef.com/helloworld?utm_source=github&utm_medium=repo&utm_campaign=shipley-integrations&utm_content=site-readme> |

## How a change gets from here to the live site

1. You edit the file and open a pull request.
2. CI checks the markup is well formed and that nothing dangerous slipped in.
3. A maintainer reviews it.
4. On merge, an operator runs the publisher script against production.
5. It is live.

Step 4 is a human on purpose. A member of our team reviews and publishes every change before
it reaches a customer. That is not distrust of you; it is the same rule we apply to ourselves,
and it is why nothing in this repository can reach the live site on its own.

## What you can change here

Wording, structure, links, headings, accessibility improvements, and fixing things that are
plainly wrong. If you want to restructure a page substantially, open an issue first so you do
not spend an evening on something we then have to argue about.

## What will get a pull request declined

- **`<script>` tags, event handlers (`onclick=`, `onload=`), `<iframe>`, or external requests.**
  These pages are served on the same domain as our checkout. CI rejects them and so will we.
- **Tracking pixels or third party embeds** of any kind.
- **Removing the security or rate limiting notices.** Those are there for a real reason.
- **Inventing facts about the farm.** If you are not sure whether something is true, ask in the
  pull request rather than guessing. We will tell you.

## House style

- Real headings in order (`h1`, then `h2`, then `h3`). Screen readers navigate by them.
- Text that makes sense without CSS or JavaScript.
- Plain language. Our readers include cattle farmers, chefs, and fourteen year olds writing
  their first pull request.
- Brand red is `#A82024`. It passes AAA contrast on white. Please do not introduce another red.
- No em dashes. House preference, applied consistently.

## Yes, the typo is on purpose

`helloworld.html` contains exactly one deliberate spelling mistake, as a first task for someone
who has never sent a pull request before. If you find it, fix it, and it is still there in
`main`, that fix is yours to make.

If you are reading this because you already fixed it: thank you, and please leave the invitation
paragraph itself intact so the next person still has a way in. Maintainers, plant a fresh one in
the same spot when the old one is merged.
