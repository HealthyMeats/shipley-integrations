# For instructors

**A real business, a real codebase, and real users, available to your class for free.**

Shipley Farms is a family cattle operation in Vilas, North Carolina. We sell beef online and
from a store on the farm. Our public tools are open, and we would rather students learn on them
than on another to-do app.

If you teach computer science, information technology, cybersecurity, data analytics, or
digital marketing, there is probably a project in here that fits your syllabus.

## What makes this different from a textbook project

**The data is real and it is messy.** Beef is sold by the pound, so a price is an estimate until
the meat is weighed. Products get renamed. Categories overlap. Students who assume clean data
will produce something that is wrong in an interesting, teachable way.

**The constraints are real.** We are a small business, not a tech company. A student who
proposes a solution needing a Kubernetes cluster has learned something useful when we say no.

**The reward is real.** A merged pull request is public, permanent, and citable. Students can
point a future employer at a commit in a working business's repository. See
[`CONTRIBUTORS.md`](../CONTRIBUTORS.md).

**Nobody can break anything.** Students never touch our production systems, never handle
customer or payment data, and cannot deploy. See
[`HOW-IT-STAYS-SEPARATE.md`](HOW-IT-STAYS-SEPARATE.md), which is worth reading before you commit
a class to this.

## What we provide

- A public product catalog as structured data, documented in [`API.md`](API.md)
- Offline fixtures so assignments work without internet access or rate limits
- A worked example client in [`examples/`](../examples/)
- Project briefs at three difficulty levels in [`PROJECTS.md`](PROJECTS.md)
- Code review from working practitioners, on the same terms as any other contributor
- A named contact who will answer a question from you or a student

## What we ask

- **No live testing of our systems.** No scanning, load testing, traffic generation, or
  automated crawling. This is the one hard rule and it is not negotiable. Everything in
  [`PROJECTS.md`](PROJECTS.md) is designed to be done against static data.
- **Tell us before the semester starts**, ideally a few weeks out, so we can seed issues at the
  right difficulty and be ready to review. A class of thirty arriving unannounced will get a
  slower response than we or your students would like.
- **Set expectations honestly.** We review carefully and we decline things. A student whose
  grade depends on their pull request being merged is in an unfair position, so please assess
  the work rather than our decision about it.

## Suggested shapes

**One class session.** Students fix the deliberate typo on
<https://shipleyfarmsbeef.com/helloworld> and open their first pull request. Most students have
never opened one. Teaching the mechanics on something that actually ships lands differently than
teaching it on a sandbox repository.

**A two-week assignment.** One starter project from [`PROJECTS.md`](PROJECTS.md) per student or
pair. Deliverable is a working tool plus a README a stranger could follow.

**A semester project.** One capstone brief per team, with a midpoint check-in. We will review at
the midpoint if you tell us when it is.

**A cybersecurity exercise.** Several briefs are analysis and design rather than code: threat
modelling a public API, specifying an authentication model, auditing a supply chain. These
produce documents, need no access to anything, and are genuinely useful to us.

## Assessment, honestly

A merged pull request is a reasonable signal but a bad grade. We merge on whether something is
useful to us, which depends on our priorities as much as on the student's work. Better signals:

- Did they read the existing documentation before asking?
- Did they handle the catch weight rule correctly? It is the one domain trap, it is documented,
  and missing it is a reliable indicator of skimming.
- Does it work offline against the fixtures?
- Could a stranger run it from the README?
- When review feedback came back, did they engage with it?

## Getting in touch

Open an issue with the `education` label, or email <gray@shipleyfarmsbeef.com>. Tell us the
course, roughly how many students, and when it runs.

We are just outside Boone. If you are local, we are open to a farm visit for a class, and to a
conversation about what would genuinely help your students rather than what we happen to want
built.
