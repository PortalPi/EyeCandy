"""Checks for feedback_phone.py's pure parts. Run: python .github/scripts/test_feedback_phone.py"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import feedback_phone as fp  # noqa: E402

failed = []


def check(name, ok):
    print(("PASS " if ok else "FAIL ") + name)
    if not ok:
        failed.append(name)


# The phone line comes from the sort's comment.
body = "<!-- eyecandy-sort: ask -->\nPhone: A player wants the FPS number bigger.\n\n**What the player said:** ..."
check("asks only on the marker as first line", fp.is_ask(body) and not fp.is_ask("hi\n" + body))
check("phone line read", fp.phone_line(body) == "A player wants the FPS number bigger.")
check("missing phone line has a fallback", fp.phone_line("<!-- eyecandy-sort: ask -->\nno line") == "A player's comment may need a fix. Open to read it.")
check("phone line is cut", len(fp.phone_line("<!-- eyecandy-sort: ask -->\nPhone: " + "x" * 500)) <= fp.PHONE_MAX)

# The notice only tells: it opens the comment and has no buttons.
msg = fp.notice("topic-abc", "Eye Candy", "Line.", "https://github.com/o/r/issues/12#issuecomment-1")
check("notice goes to the topic", msg["topic"] == "topic-abc")
check("notice opens the comment", msg["click"] == "https://github.com/o/r/issues/12#issuecomment-1")
check("notice has no buttons", "actions" not in msg)

# An earlier answer is the bot's own marker comment; nobody else's counts.
mine = {"user": {"login": "github-actions[bot]"}, "body": fp.DONE + " yes -->\nx"}
check("the bot's marker is an answer", fp.answered([mine]))
check("a stranger's marker is not", not fp.answered([{**mine, "user": {"login": "someone"}}]))
check("a bot comment without the marker is not", not fp.answered([{**mine, "body": "hello"}]))
check("no user is not", not fp.answered([{"body": fp.DONE}]))
check("no comments is not", not fp.answered([]) and not fp.answered(None))

# What to do with an ask just posted.
open_issue = {"state": "open", "labels": []}
check("an open issue goes", fp.yes_plan(open_issue, []) == "go")
check("a closed issue does not", fp.yes_plan({"state": "closed", "labels": []}, []) == "closed")
check("a held issue waits", fp.yes_plan({"state": "open", "labels": [{"name": "hold"}]}, []) == "hold")
check("another label does not hold", fp.yes_plan({"state": "open", "labels": [{"name": "bug"}]}, []) == "go")
labelled = {"state": "open", "labels": [{"name": "claude-fix"}]}
check("an answered and labelled issue is not answered twice", fp.yes_plan(labelled, [mine]) == "answered")
check("a comment with no label yet is finished", fp.yes_plan(open_issue, [mine]) == "go")
check("a label with no comment is finished", fp.yes_plan(labelled, []) == "go")
check("a missing labels list goes", fp.yes_plan({"state": "open"}, None) == "go")

print("ALL PASS" if not failed else f"{len(failed)} FAILED")
sys.exit(1 if failed else 0)
