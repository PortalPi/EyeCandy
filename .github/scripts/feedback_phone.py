"""The maintainer's phone side of the feedback pipeline: the ask, and the Yes or No coming back.

- ask (run by .github/workflows/feedback-ask.yml): the sort routine's comment on an issue starts
  with <!-- eyecandy-sort: ask --> and has a line "Phone: ...". This sends that line to the
  maintainer's ntfy topic as a phone notification. Tapping it opens the comment (the readable page). It has two
  buttons, "Yes, fix it" and "No", each posting "<yes|no> <issue> <code>" to the topic's reply
  topic, "<topic>-reply".
- answer (run by .github/workflows/feedback-answer.yml every 10 minutes): reads the last 12 hours
  of the reply topic (all ntfy.sh keeps). Yes adds the label claude-fix, which starts the fix
  routine. No closes the issue as not planned. Each leaves a comment starting
  <!-- eyecandy-answer: and sends the maintainer one line saying it was done. A tap no newer than that
  comment is skipped, so the same tap read again by a later run never acts twice, and an old No
  never closes an issue reopened since.
- The code is an HMAC of the verb and the issue number with APPROVE_KEY (an Actions secret), so
  only a notification this sent can say yes, and only for its own issue. The topic name
  (NTFY_TOPIC, an Actions secret) is never printed.

Server: ntfy.sh (chosen 17 Nov 2026). It limits requests per sending address, and GitHub's runners
share addresses, so a 429 is tried again. Standard library only.
"""

import datetime
import hashlib
import hmac
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

SERVER = "https://ntfy.sh"
ASK = "<!-- eyecandy-sort: ask -->"
PHONE_MAX = 200
FALLBACK = "A player's comment may need a fix. Open to read it."
REPLY = re.compile(r"\A(yes|no) ([0-9]{1,9}) ([0-9a-f]{16})\Z")
LABEL = "claude-fix"
WINDOW = "12h"  # as long as ntfy.sh keeps a message
DONE = "<!-- eyecandy-answer:"
BOT = "github-actions[bot]"
TRIES = 4


# ---- pure parts (checked in test_feedback_phone.py) ----


def code(key, verb, issue):
    return hmac.new(key.encode(), f"{verb}:{int(issue)}".encode(), hashlib.sha256).hexdigest()[:16]


def read_reply(text, key):
    """(verb, issue) for a reply with a good code, else None."""
    m = REPLY.match((text or "").strip())
    if not m or not key:
        return None
    verb, issue = m.group(1), int(m.group(2))
    return (verb, issue) if hmac.compare_digest(m.group(3), code(key, verb, issue)) else None


def is_ask(body):
    return (body or "").startswith(ASK)


def phone_line(body):
    for line in (body or "").splitlines():
        if line.startswith("Phone:"):
            text = " ".join(line[len("Phone:"):].split())
            if text:
                return text[:PHONE_MAX]
    return FALLBACK


def done_at(comment):
    """When this workflow did an answer, as epoch seconds, from its own marker comment; else -1.
    Only github-actions[bot]'s comments count, so nobody else can block a tap."""
    if (comment.get("user") or {}).get("login") != BOT or not (comment.get("body") or "").startswith(DONE):
        return -1
    try:
        return int(datetime.datetime.fromisoformat(comment["created_at"].replace("Z", "+00:00")).timestamp())
    except (KeyError, TypeError, ValueError, AttributeError):
        return -1


def ask_message(topic, issue, line, url, key):
    def button(label, verb):
        return {"action": "http", "label": label, "url": f"{SERVER}/{topic}-reply", "method": "POST",
                "body": f"{verb} {issue} {code(key, verb, issue)}", "clear": True}

    return {"topic": topic, "title": f"Eye Candy: a player's comment (#{issue})", "message": line,
            "click": url, "actions": [button("Yes, fix it", "yes"), button("No", "no")]}


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


def notify(topic, title, line):
    http(SERVER + "/", {"topic": topic, "title": title, "message": line})


def ask():
    body = os.environ.get("COMMENT_BODY", "")
    if not is_ask(body):
        print("Not an ask; nothing sent.")
        return
    issue = int(os.environ["ISSUE"])
    http(SERVER + "/", ask_message(os.environ["NTFY_TOPIC"], issue, phone_line(body),
                                   os.environ["COMMENT_URL"], os.environ["APPROVE_KEY"]))
    print(f"Asked about #{issue}.")


def answer():
    topic, key = os.environ["NTFY_TOPIC"], os.environ["APPROVE_KEY"]
    repo, token = os.environ["GITHUB_REPOSITORY"], os.environ["GH_TOKEN"]
    lines = http(f"{SERVER}/{topic}-reply/json?poll=1&since={WINDOW}", raw=True) or ""
    replies = []
    for line in lines.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        got = read_reply(event.get("message"), key) if event.get("event") == "message" else None
        if got and isinstance(event.get("time"), int):
            replies.append((event["time"], *got))
    print(f"{len(replies)} good replies in the last {WINDOW}.")
    failed = 0
    for when, verb, n in sorted(replies):
        try:
            act(repo, token, topic, when, verb, n)
        except (RuntimeError, KeyError, TypeError, ValueError) as e:
            failed += 1
            print(f"#{n}: not done ({e}).")
    if failed:
        sys.exit(f"{failed} replies were not done; the next run tries them again.")


def act(repo, token, topic, when, verb, n):
    """Do one tap, unless an answer to this issue was already done at or after it."""
    api = f"https://api.github.com/repos/{repo}/issues/{n}"
    issue = http(api, token=token)
    if "pull_request" in issue:
        return
    comments = http(api + "/comments?per_page=100", token=token)
    if any(done_at(c) >= when for c in comments):
        return  # this tap, or a later one, was already done
    if issue["state"] != "open":
        return
    if verb == "yes":
        http(api + "/labels", {"labels": [LABEL]}, token)
        http(api + "/comments", {"body": DONE + " yes -->\nThe maintainer said yes. A fix is on its way."}, token)
        notify(topic, "Eye Candy", f"Yes heard. Fixing #{n} now.")
        print(f"#{n}: labelled {LABEL}.")
    else:
        http(api + "/comments", {"body": DONE + " no -->\nThe maintainer said no to this one for now."}, token)
        http(api, {"state": "closed", "state_reason": "not_planned"}, token, method="PATCH")
        notify(topic, "Eye Candy", f"No heard. Closed #{n}.")
        print(f"#{n}: closed as not planned.")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("ask", "answer"):
        sys.exit("Use: feedback_phone.py ask|answer")
    ask() if sys.argv[1] == "ask" else answer()
