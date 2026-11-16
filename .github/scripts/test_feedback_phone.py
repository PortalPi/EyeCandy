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


KEY = "k" * 40

# The code ties a verb to one issue, and only the key makes it.
c = fp.code(KEY, "yes", 12)
check("code is 16 hex characters", len(c) == 16 and all(ch in "0123456789abcdef" for ch in c))
check("code differs by issue", c != fp.code(KEY, "yes", 13))
check("code differs by verb", c != fp.code(KEY, "no", 12))
check("code differs by key", c != fp.code("other key", "yes", 12))

check("a good reply reads", fp.read_reply(f"yes 12 {c}", KEY) == ("yes", 12))
check("a reply with spaces around reads", fp.read_reply(f"  yes 12 {c}\n", KEY) == ("yes", 12))
check("a wrong code is refused", fp.read_reply("yes 12 0000000000000000", KEY) is None)
check("a code for another issue is refused", fp.read_reply(f"yes 13 {c}", KEY) is None)
check("yes's code does not make a no", fp.read_reply(f"no 12 {c}", KEY) is None)
check("other words are refused", fp.read_reply("hello there", KEY) is None)
check("nothing is refused", fp.read_reply(None, KEY) is None)
check("no key refuses everything", fp.read_reply(f"yes 12 {c}", "") is None)

# The phone line comes from the sort's comment.
body = "<!-- eyecandy-sort: ask -->\nPhone: A player wants the FPS number bigger.\n\n**What the player said:** ..."
check("asks only on the marker as first line", fp.is_ask(body) and not fp.is_ask("hi\n" + body))
check("phone line read", fp.phone_line(body) == "A player wants the FPS number bigger.")
check("missing phone line has a fallback", fp.phone_line("<!-- eyecandy-sort: ask -->\nno line") == "A player's comment may need a fix. Open to read it.")
check("phone line is cut", len(fp.phone_line("<!-- eyecandy-sort: ask -->\nPhone: " + "x" * 500)) <= fp.PHONE_MAX)

msg = fp.ask_message("topic-abc", 12, "Line.", "https://github.com/o/r/issues/12#issuecomment-1", KEY)
check("ask goes to the topic", msg["topic"] == "topic-abc")
check("ask opens the readable page", msg["click"] == "https://github.com/o/r/issues/12#issuecomment-1")
check("two buttons, Yes first", [a["label"] for a in msg["actions"]] == ["Yes, fix it", "No"])
yes = msg["actions"][0]
check("Yes posts to the reply topic", yes["action"] == "http" and yes["method"] == "POST" and yes["url"] == "https://ntfy.sh/topic-abc-reply")
check("Yes carries its code", yes["body"] == f"yes 12 {c}")
check("buttons clear the notice", all(a["clear"] for a in msg["actions"]))
check("title names the issue", msg["title"] == "Eye Candy: a player's comment (#12)")

# An answer's own comment says when it was done; nobody else's counts.
mine = {"user": {"login": "github-actions[bot]"}, "body": fp.DONE + " yes -->\nx", "created_at": "2026-11-17T00:00:10Z"}
check("done time read from the bot's marker comment", fp.done_at(mine) == 1794873610)
check("a stranger's marker does not count", fp.done_at({**mine, "user": {"login": "someone"}}) == -1)
check("a bot comment without the marker does not count", fp.done_at({**mine, "body": "hello"}) == -1)
check("a bad date does not count", fp.done_at({**mine, "created_at": "soon"}) == -1)
check("no user does not count", fp.done_at({"body": fp.DONE}) == -1)

print("ALL PASS" if not failed else f"{len(failed)} FAILED")
sys.exit(1 if failed else 0)
