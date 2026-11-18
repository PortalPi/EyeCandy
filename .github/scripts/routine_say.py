"""Posts what a cloud routine wrote, as github-actions[bot], so it reaches GitHub as written.

Checked 17 Nov 2026: a comment the cloud routines post through the GitHub API (with gh or curl,
new or edited) gets a footer added on the way. A branch they push arrives as written. So a routine
never posts. It pushes a branch, and .github/workflows/routine-say.yml runs this:

- claude/say-<issue>-sort or claude/say-<issue>-fix: one empty commit whose message is the
  comment. Its first line must be one of the markers in MARKERS. This posts it on the issue, then
  deletes the branch. When it is an ask, this also says yes (the maintainer taps nothing since
  18 Nov 2026): an answer comment, the label claude-fix, and a phone notification. The label
  hold on the issue stops that.
- claude/fix-issue-<issue>: opens the pull request, its title and body from the branch's first
  commit, unless one is open already.

Text with a link, an @mention or an email, HTML, or words about how it was written, is refused: the
job fails and nothing is posted. The workflow runs main's copy of this file; the pushed commit is
only read as text, so a branch can't change what runs with the secrets. Standard library only; the
HTTP helper is feedback_phone.py's.
"""

import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import feedback_phone as fp  # noqa: E402

API = "https://api.github.com/repos/"
SAY = re.compile(r"\Aclaude/say-([0-9]{1,9})-(sort|fix)\Z")
FIX = re.compile(r"\Aclaude/fix-issue-([0-9]{1,9})\Z")
MARKERS = {
    "sort": ("<!-- eyecandy-sort: ask -->", "<!-- eyecandy-sort: no -->"),
    "fix": ("<!-- eyecandy-fix: done -->", "<!-- eyecandy-fix: stopped -->"),
}
PREFIX = {"sort": "<!-- eyecandy-sort:", "fix": "<!-- eyecandy-fix:"}
MAX_TEXT = 4000
REFUSED = [
    (re.compile(r"https?:|mailto:|www\.|//[\w-]|\]\(|\b[\w-]+\.(com|net|org|io|gg|dev|ai|app|co|me|tv|xyz)\b", re.I),
     "a link"),
    (re.compile(r"@[A-Za-z0-9]"), "an @mention or an email"),
    (re.compile(r"[\w.-]+/[\w.-]+#[0-9]"), "a link to another repository"),
    (re.compile(r"<"), "HTML"),
    (re.compile(r"claude|anthropic|openai|chatgpt|co-authored|generated (with|by)|\bai\b|\bllm\b|\U0001F916", re.I),
     "words about how it was written"),
]


# ---- pure parts (checked in test_routine_say.py) ----


def read_ref(ref):
    """("say", issue, kind) or ("pr", issue, None) for a branch this handles, else None."""
    m = SAY.match(ref or "")
    if m:
        return ("say", int(m.group(1)), m.group(2))
    m = FIX.match(ref or "")
    if m:
        return ("pr", int(m.group(1)), None)
    return None


def refusal(text):
    """Why this text must not be posted, or None."""
    text = text or ""
    for pattern, what in REFUSED:
        if pattern.search(text):
            return what
    if len(text) > MAX_TEXT:
        return "it is too long"
    return None


def check_comment(kind, body):
    """Why this comment must not be posted, or None."""
    first, _, rest = (body or "").partition("\n")
    if first.strip() not in MARKERS[kind]:
        return "the first line is not a marker"
    if len(body) > MAX_TEXT:
        return "it is too long"
    return refusal(rest)


def posted_before(kind, comments, owner):
    """The earlier comment of this kind by the maintainer or this workflow, or None."""
    for c in comments or []:
        who = (c.get("user") or {}).get("login")
        if who in (fp.BOT, owner) and (c.get("body") or "").startswith(PREFIX[kind]):
            return c
    return None


def split_message(message):
    """(subject, body) of a commit message."""
    subject, _, body = (message or "").strip().partition("\n")
    return subject.strip(), body.strip()


# ---- network parts ----


def git(*args, check=True):
    return subprocess.run(["git", *args], check=check, capture_output=True, text=True).stdout


def all_comments(api, token):
    comments, page = [], 1
    while True:
        got = fp.http(f"{api}/comments?per_page=100&page={page}", token=token) or []
        comments += got
        if len(got) < 100:
            return comments
        page += 1


def say(repo, token, branch, issue, kind):
    body = git("log", "-1", "--format=%B", os.environ["GITHUB_SHA"]).strip()
    why = check_comment(kind, body)
    if why:
        sys.exit(f"Not posted: {why}.")
    api = f"{API}{repo}/issues/{issue}"
    if "pull_request" in fp.http(api, token=token):
        sys.exit(f"Not posted: #{issue} is a pull request.")
    old = posted_before(kind, all_comments(api, token), repo.split("/")[0])
    url = None
    if old and (old.get("body") or "").strip() != body:
        print(f"#{issue} has a {kind} comment already; nothing posted.")
    elif old:
        url = old["html_url"]
        print(f"#{issue}: this comment is there already (a rerun).")
    else:
        url = fp.http(api + "/comments", {"body": body}, token)["html_url"]
        print(f"Posted on #{issue}.")
    if url and fp.is_ask(body):
        say_yes(repo, token, issue, url, fp.phone_line(body))
    git("push", "origin", "--delete", branch, check=False)  # already gone on a rerun


def say_yes(repo, token, issue, url, line):
    """The maintainer taps nothing (18 Nov 2026): an ask is a yes. Post the answer comment the fix
    routine looks for, then the label that starts it, then tell the phone. A held, closed or already
    answered issue is left alone, so a rerun never starts a second fix."""
    api = f"{API}{repo}/issues/{issue}"
    topic = os.environ["NTFY_TOPIC"]
    comments = all_comments(api, token)
    plan = fp.yes_plan(fp.http(api, token=token), comments)
    if plan == "go":
        if not fp.answered(comments):
            fp.http(api + "/comments", {"body": fp.DONE + " yes -->\nThe sort said this fits. A fix is on its way."}, token)
        fp.http(api + "/labels", {"labels": [fp.LABEL]}, token)
        fp.notify(topic, "Eye Candy: fixing", line, url)
    elif plan == "hold":
        fp.notify(topic, "Eye Candy: held", f"{line} It has the hold label, so no fix was started.", url)
    print(f"#{issue}: {plan}.")


def open_pr(repo, token, branch):
    owner = repo.split("/")[0]
    if fp.http(f"{API}{repo}/pulls?state=open&head={owner}:{branch}", token=token):
        print("A pull request is open already.")
        return
    first = git("log", "--reverse", "--format=%H", "origin/main.." + os.environ["GITHUB_SHA"]).split()
    if not first:
        sys.exit("No commits ahead of main; no pull request opened.")
    title, body = split_message(git("log", "-1", "--format=%B", first[0]))
    why = refusal(title + "\n" + body) or (None if title else "no subject")
    if why:
        sys.exit(f"No pull request opened: {why}.")
    pr = fp.http(f"{API}{repo}/pulls", {"title": title, "body": body, "head": branch, "base": "main"}, token)
    print(f"Opened pull request #{pr['number']}.")


if __name__ == "__main__":
    branch = os.environ["GITHUB_REF_NAME"]
    got = read_ref(branch)
    if not got:
        sys.exit(f"Not a branch this handles: {branch}")
    repo, token = os.environ["GITHUB_REPOSITORY"], os.environ["GH_TOKEN"]
    if got[0] == "say":
        say(repo, token, branch, got[1], got[2])
    else:
        open_pr(repo, token, branch)
