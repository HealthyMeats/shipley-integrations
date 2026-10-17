# Maintaining this

The runbook for the typo relay and the `/helloworld` page.

It exists because the relay has stalled three times — 2026-10-03, 2026-10-12 and 2026-10-15 —
and every time the cause was a step that nobody owned, not a step somebody got wrong. The
symptom is always the same and it is invisible from inside the repository: `main` is correct and
green while the live page invites strangers to fix a typo that has already been fixed, merged and
publicly credited.

## Who can do what

| Task | Who |
|---|---|
| Review, reply, merge, plant the next seed, open the next task, credit the contributor | Any maintainer with write access |
| Publish the merged page to the live site | Whoever has the storefront's API credentials, on the machine that holds them |
| Repository settings: rulesets, Actions policy, secrets, topics, social preview | The `HealthyMeats` account only |

The middle row is the seam, and it is the one that has bitten every time. Publishing needs
credentials that deliberately do not live in this repository, so a full cycle currently needs two
people. The bottom row is a property of GitHub, not a choice: this repository is owned by a
personal account, and write is the highest level a collaborator on a personal repository can
hold.

## One full cycle

### 1. A fix arrives

Check three things, in this order:

- **CI is green.** Eight checks run on a pull request. Seven are automatic; the eighth is the
  sign-off, which is the only one a contributor has to do anything about.
- **The diff is the seed and nothing else.** A relay fix is one file, one word, `+1 −1`. Anything
  larger is welcome but it is no longer a relay fix, so read it properly.
- **It is the *current* seed.** `site/SEEDED.md` names the seed number and holds the word as a
  SHA-256 hash. A fix for a seed that has already been retired means the live page is stale —
  go to step 6 before anything else.

### 2. Reply

Say something, even one line. Three of the four merged contributions got no comment at all, and
the one contributor we lost closed their own correct fix 35 minutes after a red check with
nobody having spoken to them. A reply costs a minute and is the entire difference between a
person who comes back and a person who does not.

### 3. If the sign-off is missing

Ask; never add it yourself. `maintainer_can_modify` is usually true on these pull requests, so
pushing the sign-off is mechanically possible — and it forges the one thing the sign-off
certifies. `CONTRIBUTING.md` says a human signs and is accountable, and `git blame` would show
us doing it.

The failing check prints the browser path, and `CONTRIBUTING.md` has it too. Point at it kindly
and say we would rather help them redo it than close their work.

### 4. Merge

Merge commits are the house style here; the history reads `Merge pull request #N from …`.

### 5. Plant the next seed, in the same sitting

```
python3 tools/plant_seed.py --credit @their-handle --fixed <the word just fixed> \
    --correct <a correctly spelled word on the page> --misspell <how to misspell it>
```

`--fixed` is checked against the retired seed's hash, so the chain cannot record the wrong word.
The tool rewrites the page, updates the ledger, moves the retired seed into the chain, credits
the contributor and prints the publish command. `--dry-run` says what it would do and writes
nothing.

Pick a word in ordinary prose that a person reads. Never inside `<code>`, `<script>` or
`<style>`, never in an attribute, URL or email address, never in a product name or price, and
never in the invitation paragraph itself. `site/SEEDED.md` has the full rule and the tool
enforces most of it.

### 6. Publish — the handoff

**Nothing above this line is visible to the public until this step runs.** The page on the
storefront is a copy; merging changes the repository, not the page.

```
git -C shipley-integrations pull --ff-only origin main
```

then, on the machine with the storefront credentials:

```
PROD_CONFIRM=1 SITE_URL=https://shipleyfarmsbeef.com \
    python3 launch-automation/prod-queue/360_helloworld_page.py --apply
```

Run it without the last flag first to see the plan. It is idempotent, it refuses to publish from
a checkout that does not match `origin/main`, it checks every link on the page before writing,
and it records an undo file so the previous page can be restored exactly.

The pull is not hygiene. The publisher reads a local checkout, and a checkout that is behind
publishes the old page *and verifies itself as correct*, because it compares the live page to
the same stale file. That is precisely how this failed on 2026-10-03 and again on 2026-10-12.

**This runs twice per cycle:** once after the merge, once after the new seed is planted.

### 7. Open the next task, after the page is verified

Not before. An issue that points at a page still serving the previous seed sends the next person
to look for something that is not there — which is what happened to issue #11. Reuse the body of
the most recent relay issue verbatim; it has been through four contributors and it works.

Title: `Find and fix the deliberate typo on /helloworld`.
Labels: `documentation`, `good first issue`.

### 8. Credit

`plant_seed.py` writes the ledger row. Add the `CONTRIBUTORS.md` row yourself, **at the top** —
the table is newest first — citing the pull request, not the issue.

## The two checks, and the difference between them

- **`The typo relay still has a way in`** (in CI, on every push and pull request) reads the
  repository file. It fails `main` when a seed has been fixed and not replaced, so the relay
  cannot quietly stop.
- **`Live seed`** (its own workflow, on a schedule) fetches the published page and fails when the
  page does not carry the seed the ledger names. It is the only check that can see step 6.

A green `main` is not evidence that the live page matches the repository. Only the second check
says that, and it runs on GitHub's schedule rather than on demand — in practice every few hours,
not every hour, because GitHub throttles scheduled workflows on a quiet repository. A maintainer
can start it by hand from the Actions tab once step 6 is done, rather than waiting.

When `Live seed` is red, step 6 is owed. It is not a flaky check and it has never produced a
false alarm: an unreachable storefront is reported as "could not verify" and passes.

## Order that actually matters

1. Publish before opening the next task.
2. Pull before publishing.
3. Plant before the second publish — `plant_seed.py` refuses to plant while the retired seed is
   still on the live page, which is the tool telling you step 6 has not happened yet.

## If you inherit this

Read `site/SEEDED.md` first: it is the ledger, it explains where a seed is allowed to live, and
it is what CI reads. Then `CONTRIBUTING.md` for what we ask of contributors, and
`CODE_OF_CONDUCT.md` for how we behave when one of them is having a bad day.
