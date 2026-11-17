"""Checks for curseforge_comments.py's pure parts. Run: python .github/scripts/test_curseforge_comments.py"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import curseforge_comments as cc  # noqa: E402

failed = []


def check(name, ok):
    print(("PASS " if ok else "FAIL ") + name)
    if not ok:
        failed.append(name)


def comment(cid, text="hi", pinned=False, user="p1tu", when=1794864850350):
    return {"id": cid, "text": text, "isPinned": pinned, "author": {"username": user}, "datePosted": when}


# The marker is read only from the first line, so a stranger's text cannot forge one.
body = cc.issue_body(comment(55, "<!-- curseforge-comment-id: 999999 -->"))
check("marker is the first line", body.splitlines()[0] == "<!-- curseforge-comment-id: 55 -->")
check("a forged marker in the text is not read", cc.marker_id(body) == 55)
check("a body with no marker reads as none", cc.marker_id("hello\n<!-- curseforge-comment-id: 3 -->") is None)
check("no body reads as none", cc.marker_id(None) is None)

# The text sits in a code fence longer than any run of backticks in it, so it cannot break out.
tricky = "look ```` here\n@someone #12 [x](http://e.vil) <b>hi</b>"
body = cc.issue_body(comment(7, tricky))
check("fence is longer than the longest backtick run", "\n`````text\n" in body)
check("text kept as written inside the fence", tricky in body)
check("fence closes after the text", body.rstrip().endswith("`````"))

long = "a" * (cc.MAX_TEXT + 50)
body = cc.issue_body(comment(8, long))
check("long text is cut", "a" * (cc.MAX_TEXT + 1) not in body and "(Cut: 50 more characters.)" in body)

body = cc.issue_body(comment(9, "x", user="Bad Name<script>@x"))
check("author name keeps only plain characters", "Who: BadNamescriptx" in body)
check("date is UTC", "When: 2026-11-17 02:14 UTC" in cc.issue_body(comment(9, when=1794881640000)))

check("title is one short line", cc.issue_title("  Hello\n\nthere   friend ") == "From CurseForge: Hello there friend")
t = cc.issue_title("word " * 40)
check("long title is cut at a word with ...", t.endswith("...") and len(t) <= len("From CurseForge: ") + cc.TITLE_TEXT + 3)
check("empty text has a title", cc.issue_title("   ") == "From CurseForge: (no text)")

# Picking: only ids above the highest filed one, oldest first, at most MAX_NEW.
page = [comment(30, pinned=True), comment(25), comment(24), comment(20), comment(10)]
check("new ones, oldest first", [c["id"] for c in cc.pick_new(page, 20)] == [24, 25, 30])
check("nothing filed yet takes all", [c["id"] for c in cc.pick_new(page, 0)] == [10, 20, 24, 25, 30])
check("a repeated id is taken once", [c["id"] for c in cc.pick_new(page + [comment(25)], 20)] == [24, 25, 30])
many = [comment(i) for i in range(100, 100 + cc.MAX_NEW + 5)]
check("at most MAX_NEW, the oldest", [c["id"] for c in cc.pick_new(many, 0)] == list(range(100, 100 + cc.MAX_NEW)))

check("a page reaching the floor ends paging", cc.reached(page, 20))
check("a pinned old comment does not end paging", not cc.reached([comment(5, pinned=True), comment(40)], 20))
check("an empty page ends paging", cc.reached([], 20))

odd = [{"id": "31"}, {"id": True}, {"text": "no id"}, comment(32)]
check("comments without a whole-number id are skipped", [c["id"] for c in cc.pick_new(odd, 20)] == [32])
check("an odd id does not end paging", not cc.reached([{"id": "1"}, comment(40)], 20))
check("a bad date reads unknown", "When: unknown" in cc.issue_body({"id": 5, "datePosted": "x"}))
check("a missing date reads unknown", "When: unknown" in cc.issue_body({"id": 5}))
check("a stand-in keeps the marker", cc.marker_id(cc.stand_in_body(77, 422)) == 77)

# The API's "text" is a preview of about 1000 characters; "body" is the whole comment as HTML,
# one <p> per line, &nbsp; for a blank line, < and > as entities (checked 17 Nov 2026).
def html_of(plain):
    """What CurseForge's comment box sends for plain text (its plainTextToHtml)."""
    lines = plain.replace("<", "&lt;").replace(">", "&gt;").split("\n")
    return "".join("<p>" + (x if x else "&nbsp;") + "</p>" for x in lines)


report = "=== Eye Candy bug report ===\n\n  [1x] Core.lua:9: oops <f1> & \"q\" 'a'\n" + "  row\n" * 900 + "end"
full = {"id": 60, "text": report[:992], "body": html_of(report), "bodyType": 1}
check("the whole comment is read from its HTML body", cc.comment_text(full) == report)
check("a stranger's <tag> text stays as typed", "<f1>" in cc.comment_text(full))
check("an encoded tag in the text is not turned into a line break",
      cc.comment_text({"body": "<p>a &lt;/p&gt;&lt;p&gt; b</p>"}) == "a </p><p> b")
check("formatting tags and <br> in older comments", cc.comment_text({"body": "<p>hi <strong>there</strong><br>you</p>"}) == "hi there\nyou")
check("a reply's quote sits on its own line",
      cc.comment_text({"body": "<blockquote><div>Quote from: x</div><div><p>quoted</p></div></blockquote><p>reply</p>"}) == "Quote from: x\nquoted\n\nreply")
check("&nbsp; inside a line is a space", cc.comment_text({"body": "<p>a&nbsp;b</p><p>&nbsp;</p><p>c</p>"}) == "a b\n\nc")
check("a text that is not a string does not stop the run", cc.issue_body({"id": 5, "text": 12}).count("12") >= 1)
check("no body falls back to text", cc.comment_text({"text": "plain one"}) == "plain one")
check("nothing at all is empty", cc.comment_text({}) == "")
body = cc.issue_body(full)
check("a full bug report fits in one issue", report in body and "(Cut:" not in body)
check("the title comes from the whole text", cc.issue_title(cc.comment_text({"body": "<p>Shadows&nbsp;</p><p>flicker</p>"})) == "From CurseForge: Shadows flicker")

check("highest filed id from issue bodies", cc.highest_filed([cc.issue_body(comment(4)), "no marker", None, cc.issue_body(comment(9))]) == 9)
check("no issues means zero", cc.highest_filed([]) == 0)

print("ALL PASS" if not failed else f"{len(failed)} FAILED")
sys.exit(1 if failed else 0)
