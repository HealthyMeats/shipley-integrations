"""The safety gate for the markup in `site/`, mirrored from the publisher.

READ THIS BEFORE YOU EDIT IT
----------------------------
Files in `site/` are published verbatim as live pages on https://shipleyfarmsbeef.com, which
is the same origin as our checkout. So markup contributed here is not a document, it is code
running where our customers' sessions live. That is why the rules below are strict about
things that would be unremarkable in an ordinary web page.

This file is a COPY, provided so your pull request gets a verdict from CI instead of from a
maintainer discovering it at publish time. The real gate runs on the operator's machine and is
not in this repository, for the plain reason that a gate stored in the repository it polices
could be edited by the same pull request it is meant to stop. The two are run over a shared
attack corpus and any disagreement between them is treated as a failure, so weakening this
copy does not weaken the gate. It just gets noticed.

If the gate refuses something you believe is reasonable, that is worth an issue. Several of
the allowed tags and attributes are here because somebody asked. What will not be relaxed is
anything that can run script, fetch from another host, cover the page, or redirect a visitor.

The rest of this file is the mirrored implementation, comments included, so you can see
exactly what your markup is being judged against.
"""
import html
import html.parser
import re
from urllib.parse import urlsplit

# Exact hostnames. Not a substring test, not a suffix test: the whole point of the rewrite.
ALLOWED_HOSTS = frozenset((
    "shipleyfarmsbeef.com",
    "www.shipleyfarmsbeef.com",
    "github.com",
    "healthymeats.github.io",
))

# Nothing here is bigger than a page of prose. A 5 MB "page" is a performance fault, not a
# contribution, and refusing it early keeps it out of the Web Page field entirely.
MAX_BYTES = 200 * 1024
MAX_STYLE_LENGTH = 300

# Attributes any allowed tag may carry. `id` is deliberately absent: an attacker-chosen id on
# an origin that runs the storefront's own JavaScript is the DOM-clobbering class, nothing on
# these pages needs one, and the refusal message tells a contributor to just ask.
GLOBAL_ATTRS = frozenset(("class", "title", "lang", "dir", "style"))

# tag -> the attributes it may carry ON TOP of GLOBAL_ATTRS.
ALLOWED_TAGS = {
    "a": frozenset(("href", "rel", "target")),
    "abbr": frozenset(),
    "article": frozenset(),
    "aside": frozenset(),
    "b": frozenset(),
    "blockquote": frozenset(("cite",)),
    "br": frozenset(),
    "caption": frozenset(),
    "code": frozenset(),
    "dd": frozenset(),
    "del": frozenset(),
    "details": frozenset(("open",)),
    "div": frozenset(),
    "dl": frozenset(),
    "dt": frozenset(),
    "em": frozenset(),
    "figcaption": frozenset(),
    "figure": frozenset(),
    "footer": frozenset(),
    "h1": frozenset(),
    "h2": frozenset(),
    "h3": frozenset(),
    "h4": frozenset(),
    "h5": frozenset(),
    "h6": frozenset(),
    "header": frozenset(),
    "hr": frozenset(),
    "i": frozenset(),
    "img": frozenset(("src", "alt", "width", "height", "loading", "decoding")),
    "ins": frozenset(),
    "li": frozenset(("value",)),
    "mark": frozenset(),
    "nav": frozenset(),
    "ol": frozenset(("start", "reversed", "type")),
    "p": frozenset(),
    "pre": frozenset(),
    "s": frozenset(),
    "section": frozenset(),
    "small": frozenset(),
    "span": frozenset(),
    "strong": frozenset(),
    "sub": frozenset(),
    "summary": frozenset(),
    "sup": frozenset(),
    "table": frozenset(),
    "tbody": frozenset(),
    "td": frozenset(("colspan", "rowspan")),
    "tfoot": frozenset(),
    "th": frozenset(("colspan", "rowspan", "scope")),
    "thead": frozenset(),
    "tr": frozenset(),
    "u": frozenset(),
    "ul": frozenset(),
}

VOID = frozenset(("area", "base", "br", "col", "embed", "hr", "img", "input", "link",
                  "meta", "param", "source", "track", "wbr"))

# Refused by the allowlist anyway. Named here only so the message says WHY this particular tag
# is a problem on this particular origin, instead of "not on the list".
TAG_REASONS = {
    "script": "it executes code on the origin that holds the customer's checkout session",
    "style": "a stylesheet can cover or restyle the checkout chrome. Use a style attribute",
    "link": "it can pull a stylesheet from anywhere, including off this site",
    "base": "it silently retargets every relative link and image on the page",
    "meta": "meta refresh redirects the visitor off this site from our own domain",
    "iframe": "it embeds another document inside ours",
    "object": "it embeds a plugin document inside ours",
    "embed": "it embeds a plugin document inside ours",
    "form": "a form on our origin can be pointed at somebody else's server",
    "input": "an input on a page like this is either a form or a decoy",
    "button": "a button here has nothing legitimate to submit",
    "textarea": "a textarea here has nothing legitimate to submit",
    "select": "a select here has nothing legitimate to submit",
    "svg": "SVG carries its own scriptable elements and attributes",
    "math": "MathML carries its own scriptable attributes",
    "template": "its contents are invisible to review and live to script",
    "noscript": "its contents are invisible to review in a normal browser",
    "canvas": "there is nothing on these pages for it to draw",
    "audio": "media belongs on a product page, not here",
    "video": "media belongs on a product page, not here",
    "frame": "framesets are not used anywhere on this site",
    "frameset": "framesets are not used anywhere on this site",
    "marquee": "no",
}

_CSS_FORBIDDEN = (
    (re.compile(r"url\s*\(", re.I),
     "url(...), which fetches something from off this page"),
    (re.compile(r"expression\s*\(", re.I), "a CSS expression()"),
    (re.compile(r"@\s*import", re.I), "an @import"),
    (re.compile(r"(-moz-)?binding\s*:", re.I), "a binding, which can attach script"),
    (re.compile(r"behaviou?r\s*:", re.I), "a behavior, which can attach script"),
    (re.compile(r"position\s*:", re.I),
     "a position declaration. A fixed or absolute box can cover the whole page, including "
     "the checkout, and collect what the visitor types into it"),
    (re.compile(r"/\*"), "a CSS comment. Please keep these values to plain declarations"),
    (re.compile(r"[<>]"), "an angle bracket"),
)

# Browsers strip these before deciding whether they are looking at a scheme, so we strip them
# before deciding too. `java\tscript:` and `&#106;avascript:` both arrive here as javascript:.
_CONTROL_CHARS = re.compile(r"[\x00-\x20\x7f]")
_TAG_OPENER = re.compile(r"<[A-Za-z!/?]")


def _url_problem(raw):
    """Return a human explanation if this href/src may not be published, else None."""
    value = _CONTROL_CHARS.sub("", html.unescape(raw or ""))
    if not value:
        return "is empty"
    if value.startswith("//"):
        return ("is protocol-relative ({!r}). Write the full https:// URL so the host can be "
                "checked".format(raw[:60]))
    try:
        parts = urlsplit(value)
    except ValueError as e:
        return "could not be parsed as a URL ({})".format(str(e)[:60])

    scheme = (parts.scheme or "").lower()
    if not scheme:
        # A relative path or an in-page fragment. Cannot leave this site, so it is fine.
        return None
    if scheme in ("mailto", "tel"):
        return None
    if scheme != "https":
        return ("uses the {!r} scheme. Only https, mailto and tel are allowed, and a relative "
                "path is better still".format(scheme))
    if parts.username or parts.password:
        return ("carries a username before the host, which is how a link is made to LOOK like "
                "it points at an allowed site")
    host = (parts.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        return ("points at {!r}, which is not one of: {}".format(
            host or "(no host)", ", ".join(sorted(ALLOWED_HOSTS))))
    if parts.port not in (None, 443):
        return "uses port {}, which is not 443".format(parts.port)
    return None


def _style_problem(value):
    """Return a human explanation if this style attribute may not be published, else None."""
    if len(value) > MAX_STYLE_LENGTH:
        return ("is {} characters long. Keep inline style to the few declarations the page "
                "actually needs".format(len(value)))
    for pattern, what in _CSS_FORBIDDEN:
        if pattern.search(value):
            return "contains {}".format(what)
    return None


class _Gate(html.parser.HTMLParser):
    """Walks the markup once, recording every problem and every construct's position.

    The positions matter as much as the problems: layer 3 compares what the parser read as a
    tag against every `<` in the raw bytes, and anything the parser skipped is a place where a
    browser and this validator could disagree.
    """

    def __init__(self, markup):
        html.parser.HTMLParser.__init__(self)
        self.markup = markup
        self.problems = []
        self.stack = []
        self.headings = []
        self.construct_offsets = set()
        self._line_starts = [0]
        for m in re.finditer(r"\n", markup):
            self._line_starts.append(m.end())

    # -- position bookkeeping ---------------------------------------------------------------
    def _offset(self):
        lineno, col = self.getpos()
        try:
            return self._line_starts[lineno - 1] + col
        except IndexError:
            return -1

    def _note(self):
        self.construct_offsets.add(self._offset())

    def _say(self, message):
        self.problems.append("line {}: {}".format(self.getpos()[0], message))

    # -- tags ------------------------------------------------------------------------------
    def handle_starttag(self, tag, attrs):
        self._note()
        self._check_tag(tag, attrs)
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self._note()
        self._check_tag(tag, attrs)

    def handle_endtag(self, tag):
        self._note()
        if tag in VOID:
            return
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        elif tag in self.stack:
            self._say("</{}> closes out of order. Close the inner tag first".format(tag))
            while self.stack and self.stack[-1] != tag:
                self.stack.pop()
            if self.stack:
                self.stack.pop()
        else:
            self._say("</{}> closes a tag that was never opened".format(tag))

    def _check_tag(self, tag, attrs):
        if tag not in ALLOWED_TAGS:
            reason = TAG_REASONS.get(tag)
            if reason:
                self._say("<{}> is not allowed here, because {}.".format(tag, reason))
            else:
                self._say("<{}> is not one of the tags these pages use. Allowed: {}. If you "
                          "genuinely need it, open an issue and say what for."
                          .format(tag, ", ".join(sorted(ALLOWED_TAGS))))
            return

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.headings.append(int(tag[1]))

        permitted = GLOBAL_ATTRS | ALLOWED_TAGS[tag]
        seen = set()
        for name, value in attrs:
            name = (name or "").lower()
            value = value or ""
            if name in seen:
                self._say("<{}> repeats the {!r} attribute. Browsers keep the first and "
                          "validators often read the second".format(tag, name))
            seen.add(name)

            if name.startswith("on"):
                self._say("<{} {}=...> is an inline event handler, which runs JavaScript on "
                          "the origin that holds the checkout session. These pages carry no "
                          "script at all.".format(tag, name))
                continue
            if name not in permitted:
                self._say("<{}> may not carry {!r}. Allowed on this tag: {}"
                          .format(tag, name, ", ".join(sorted(permitted))))
                continue

            if name in ("href", "src"):
                problem = _url_problem(value)
                if problem:
                    self._say("the {} on <{}> {}".format(name, tag, problem))
            elif name == "style":
                problem = _style_problem(value)
                if problem:
                    self._say("the style attribute on <{}> {}".format(tag, problem))
            elif name == "target":
                if value != "_blank":
                    self._say("<{} target={!r}> is not used here. Only _blank, and only with "
                              'rel="noopener"'.format(tag, value))
                elif "noopener" not in (dict(attrs).get("rel") or ""):
                    self._say('<{} target="_blank"> needs rel="noopener" so the new tab '
                              "cannot reach back into this one".format(tag))

    # -- everything else the parser can report ----------------------------------------------
    def handle_comment(self, data):
        self._note()
        if "<" in data or re.search(r"\[\s*if", data, re.I):
            self._say("this comment hides markup or a conditional block. Comments here are "
                      "for explaining the file to the next person")

    def handle_decl(self, decl):
        self._note()
        self._say("<!{}> belongs to a whole HTML document. This file is a FRAGMENT that gets "
                  "placed inside our page, so it has no doctype, <html> or <body>."
                  .format(decl.split()[0] if decl.split() else decl))

    def unknown_decl(self, data):
        self._note()
        self._say("<![{}...]> is not allowed. A CDATA section parses differently in HTML than "
                  "it looks like it should".format(data[:12]))

    def handle_pi(self, data):
        self._note()
        self._say("<?{}...> is a processing instruction, which some browsers read as a "
                  "comment and some do not".format(data[:12]))


def check(markup, filename="<markup>", required=()):
    """Return a list of human-readable problems. Empty list means publishable.

    `required` is a sequence of (substring, what_it_is) that must still be present: the
    on-ramp, the source link, the automated-traffic notice, the security contact, the marker.
    A pull request fixing the planted typo must not remove the invitation that advertises it.
    """
    problems = []
    raw = len(markup.encode("utf-8"))
    if raw > MAX_BYTES:
        return ["{}: {} bytes, over the {} byte ceiling for one of these pages".format(
            filename, raw, MAX_BYTES)]

    gate = _Gate(markup)
    try:
        gate.feed(markup)
        gate.close()
    except Exception as e:
        # A parser that cannot finish is a file we must not publish, whatever the reason.
        return ["{}: could not be parsed as HTML ({}: {}). Nothing is published from a file "
                "we cannot read the same way twice.".format(filename, type(e).__name__,
                                                            str(e)[:80])]
    problems += gate.problems

    # Layer 3. Any `<` that looks like it opens a tag and that the parser did NOT report is a
    # place where a browser might see markup where we saw text. That differential is the whole
    # bypass class, so it is refused rather than reasoned about.
    for m in _TAG_OPENER.finditer(markup):
        if m.start() not in gate.construct_offsets:
            line = markup[:m.start()].count("\n") + 1
            problems.append("line {}: {!r} looks like the start of a tag but does not parse as "
                            "one. If you meant a literal angle bracket in text, write &lt;"
                            .format(line, markup[m.start():m.start() + 14]))

    if gate.stack:
        problems.append("unclosed tag(s): {}".format(", ".join(gate.stack[:5])))

    for needle, what in required:
        if needle not in markup:
            problems.append("{} is missing (looked for {!r}). A pull request should not remove "
                            "it.".format(what, needle))

    if "—" in markup:
        line = markup[:markup.index("—")].count("\n") + 1
        problems.append("line {}: contains an em dash. House style uses plain "
                        "punctuation.".format(line))

    for prev, nxt in zip(gate.headings, gate.headings[1:]):
        if nxt > prev + 1:
            problems.append("heading level jumps from h{} to h{}. Screen readers navigate by "
                            "these, so a skipped level loses people.".format(prev, nxt))
            break

    return ["{}: {}".format(filename, p) for p in problems]
