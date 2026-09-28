# Security Policy

## Reporting a vulnerability

**Email <gray@shipleyfarmsbeef.com> directly. Do not open a public issue.**

Include what you did, what happened, and roughly how bad you think it is. A rough report sent
early beats a polished one sent late.

We will acknowledge as soon as we have seen it and tell you what we found. We are a small
family business, not a security team, so we will be honest with you about timelines rather
than quiet. We would rather not quote you a number we cannot hold to.

## Safe harbour

We will not pursue legal action against anyone who reports a problem in good faith, gives us
a reasonable chance to fix it before disclosing, and stays inside the boundaries below.

## Boundaries, and why they are strict

**Do not run automated scanners, load tests, or bulk crawls against our site.**

This is a working family business, not a lab, and unsolicited automated traffic against it is
not authorised. Testing that degrades or disrupts service for customers is outside safe harbour
and we will treat it as an attack rather than as research.

Also out of scope:

- Anything involving a real customer's account, order, email address, or card
- Placing real orders, or testing payment flows against live card processing
- Social engineering of our staff, our processor, or our hosting provider
- Physical access to the farm or the store
- Denial of service of any kind

If your finding genuinely needs volume or a live transaction to demonstrate, stop and email us
first. We will find a safe way to let you show it.

## Out of scope as findings

Reports we will read but not treat as vulnerabilities: missing headers with no demonstrated
impact, rate limiting on public read endpoints (we know, it is on the roadmap), version
disclosure, and anything from an automated scanner pasted in without a working reproduction.

## No bounty

We do not run a paid bounty programme and we are not going to pretend otherwise. We will
credit you by name in the fix if you want that, and we will say thank you properly.
