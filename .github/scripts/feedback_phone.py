"""The maintainer's phone side of the feedback pipeline: a notice that a fix has started.

Since 18 Nov 2026 the maintainer taps nothing. routine_say.py posts the sort routine's comment,
and when it is an ask (it starts <!-- eyecandy-sort: ask --> and has a line "Phone: ...") it says
yes itself: a comment starting <!-- eyecandy-answer: yes, then the label claude-fix, which starts the
fix routine. This file holds the pieces that need no secret to check: what the ask looks like, the
phone line, the marker, and the small HTTP helper. The phone notification only tells; tapping it
opens the comment.

The topic name (NTFY_TOPIC, an Actions secret) is never printed. Server: ntfy.sh (chosen 17 Nov
2026). It limits requests per sending address, and GitHub's runners share addresses, so a 429 is
tried again. Standard library only.
"""

import json
import os
import time
import urllib.error
import urllib.request

SERVER = "https://ntfy.sh"
ASK = "<!-- eyecandy-sort: ask -->"
PHONE_MAX = 200
FALLBACK = "A player's comment may need a fix. Open to read it."
LABEL = "claude-fix"
HOLD = "hold"  # the maintainer's brake: an issue with this label gets no automatic yes
DONE = "<!-- eyecandy-answer:"
BOT = "github-actions[bot]"
TRIES = 4


# ---- pure parts (checked in test_feedback_phone.py) ----


def is_ask(body):
    return (body or "").startswith(ASK)


def phone_line(body):
    for line in (body or "").splitlines():
        if line.startswith("Phone:"):
            text = " ".join(line[len("Phone:"):].split())
            if text:
                return text[:PHONE_MAX]
    return FALLBACK


def answered(comments):
    """True when this workflow already said yes or no on the issue. Only github-actions[bot]'s own
    marker comments count, so nobody else can block or fake an answer."""
    return any((c.get("user") or {}).get("login") == BOT and (c.get("body") or "").startswith(DONE)
               for c in comments or [])


def yes_plan(issue, comments):
    """What to do with an ask just posted on this issue: "go", "hold", "answered" or "closed"."""
    if issue.get("state") != "open":
        return "closed"
    names = [(label or {}).get("name") for label in issue.get("labels") or []]
    if answered(comments) and LABEL in names:
        return "answered"  # a half-done earlier run (comment, no label) falls through and finishes
    if HOLD in names:
        return "hold"
    return "go"


def notice(topic, title, line, url):
    """The phone notification: a line, and a tap that opens the comment. No buttons."""
    return {"topic": topic, "title": title, "message": line, "click": url}


# ---- network parts ----


def http(url, data=None, token=None, method=None, raw=False):
    headers = {"User-Agent": "EyeCandy-feedback (+https://github.com/PortalPi/EyeCandy)"}
    if token:
        headers["Authorization"] = "Bearer " + token
        headers["Accept"] = "application/vnd.github+json"
    body = json.dumps(data).encode() if data is not None else None
    if body:
        headers["Content-Type"] = "application/json"
    for attempt in range(1, TRIES + 1):
        try:
            req = urllib.request.Request(url, body, headers, method=method)
            with urllib.request.urlopen(req, timeout=30) as r:
                text = r.read().decode()
                return text if raw else (json.loads(text) if text else None)
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == TRIES:
                raise RuntimeError(f"HTTP {e.code} from {url.split('?')[0].replace(os.environ.get('NTFY_TOPIC') or '~', '<topic>')}") from None
            time.sleep(15 * attempt)


def notify(topic, title, line, url):
    http(SERVER + "/", notice(topic, title, line, url))
