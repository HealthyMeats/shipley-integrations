# How this repository stays separate from the farm

Short version: **nothing here can reach our live systems.** Not your code, not a merged pull
request, not our own continuous integration. Every path to production ends at a person.

This matters to three different people, so it is written down rather than assumed.

## If you are a contributor

You cannot break the farm. That is by design, and it means you can experiment freely.

- Everything you build works against **public data**: the catalog file, or the fixtures in
  [`fixtures/`](../fixtures/). No account, no key, no credential, ever.
- Tests and examples in this repository **run offline**. If something only works when it can
  reach the internet, it is not finished.
- Merging your pull request changes this repository. It does not change the farm.

## If you are a maintainer

- This repository holds **no credentials, no connection strings, and no production
  configuration**. If you are about to add one, stop.
- Continuous integration runs with **no secrets** and no access to farm systems. It validates
  structure and runs offline tests. It cannot deploy, and it is not being given the ability to.
- Publishing a change to the live site is a **separate, deliberate act** performed by a team
  member from their own machine, using tooling that is not in this repository. That tooling
  checks the content before it writes anything and can reverse the change afterwards.
- A merged pull request is a **proposal that has been accepted into the repository**. It is not
  a deployment. Those are two different decisions and we keep them that way on purpose.

## If you are an instructor evaluating this for a class

Your students cannot cause a production incident here, because there is no mechanism by which
their work reaches production without a member of our team choosing to publish it, by hand,
after reading it.

What that means practically:

- No student needs an account on any farm system.
- No student handles customer data, order data, or payment data, because none of it is here and
  none of it is reachable from here.
- A student's work being merged is entirely within our control and can be assessed on its own
  merits, separately from whether we choose to run it.

## What is explicitly not in scope, for anyone

Live testing of our systems is **not authorised**. That includes scanning, load testing, traffic
generation, automated crawling, and probing for vulnerabilities. This is a working business, and
unsolicited automated traffic against it is treated as an attack rather than as research, whether
or not it was well intentioned.

If a project idea seems to need any of that, it needs a conversation first. Open an issue and
describe what you are trying to learn, and we will usually find a way to get you there with
static data instead.

Genuine security findings are welcome through the process in [`SECURITY.md`](../SECURITY.md).
