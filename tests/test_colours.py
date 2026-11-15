"""Colour means one thing (docs/ui-rules.md rule 20). The quality level stripe colours are only for
a quality level's FPS cost, Looks and Situations get no colour of their own, and every other
coloured line uses gold, grey, red or green from the table.
Run: python tests/test_colours.py"""
import os
import re

from lib import boot, check, done

GOLD, GREY, RED = "|cffffd100", "|cff9d9d9d", "|cffff4040"
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'EyeCandy')

lua = boot()
E, X = lua.eval, lua.execute
X('for k, v in pairs({ bloomUserMult = "1", cameraFov = "90", Contrast = "57", Brightness = "46" }) do C_CVar.RegisterCVar(k, v) end')
X('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}; SlashCmdList.EYECANDY("")')
P, M = 'EyeCandyMainFrame.pages.presets', 'EyeCandyMainFrame'
STRIPE = [E('NS.TIER_COLOURS[%d]' % i).lower() for i in range(1, E('#NS.TIER_COLOURS') + 1)]

# An import that skips settings says so in red: Eye Candy refuses those settings.
X('''NS.PreviewImport = function() return { ok = true, name = "Moody", author = "Sam", changes = { a = 1 },
  skipped = { "chatStyle" } } end''')
pv = E('(NS.ImportPreviewText("!EC1!x"))')
check(RED + "Skips 1 settings Eye Candy doesn't save in presets:|r chatStyle" in pv, "the import's Skips line is red (%r)" % pv)

# The card's "changed since" count is grey, like the row's own "(N changed)".
X('REAL_ON = NS.OnPreset; NS.OnPreset = function() return { id = "look:moody", name = "Moody", group = "Looks" }, 2 end; NS.RefreshUI()')
d = E(P + '.card.detail.text')
check(d == "Look. " + GREY + "2 settings changed since you applied it.|r", "the card's changed count is grey (%r)" % d)

# Something running on your settings is on now: gold, on the card and in the title.
X('NS.AutotuneNote = function() return "Autotune is testing settings" end; NS.RefreshUI()')
check(E(P + '.card.note.text') == GOLD + "Autotune is testing settings|r", "the card's running note is gold")
t = E(M + '.titleText.text')
check(t.endswith("  " + GOLD + "Autotune is testing settings|r"), "and so is the title's (%r)" % t)
X('NS.AutotuneNote = nil; NS.OnPreset = REAL_ON; NS.RefreshUI()')

# Chat lines start with a gold Eye Candy.
X('CHAT = {}; NS.Print("hello")')
check(E('CHAT[1]') == GOLD + "Eye Candy:|r hello", "chat lines start with a gold Eye Candy: (%r)" % E('CHAT[1]'))

# The AddOns list: the subtitle is grey secondary text, not Balanced's blue.
toc = open(os.path.join(ROOT, 'EyeCandy.toc'), encoding='utf-8').read()
title = re.search(r'^## Title: (.*)$', toc, re.M).group(1)
check(title == "Eye Candy " + GREY + "Graphics Presets & Hidden Settings|r", "the AddOns list subtitle is grey (%r)" % title)

# Looks and Situations get no colour of their own.
check(all(E('NS.%s[%d].colour' % (t, i)) is None for t in ('LOOKS', 'SITUATIONS') for i in range(1, E('#NS.%s' % t) + 1)),
      "no Look or Situation carries a colour")
ui = open(os.path.join(ROOT, 'UI.lua'), encoding='utf-8').read()
check('look.colour' not in ui, "the fallback Look buttons draw plain names")

# Stripe colours appear only where they mean a quality level: the stripe itself in Data.lua,
# TierColour (Showcase is the costliest quality level) and the Set all to row's Showcase button.
def tier_block(path):
    """The line numbers inside Data.lua's ns.TIER_COLOURS table."""
    lines, inside, out = open(path, encoding='utf-8').read().split('\n'), False, set()
    for n, line in enumerate(lines, 1):
        if line.startswith('ns.TIER_COLOURS = {'):
            inside = True
        elif inside and line.startswith('}'):
            break
        elif inside:
            out.add(n)
    return out


TIER_LINES = tier_block(os.path.join(ROOT, 'Data.lua'))
check(len(TIER_LINES) == len(STRIPE) + 1, "the stripe table is found in Data.lua (%d lines)" % len(TIER_LINES))
ALLOWED = {
    'Data.lua': lambda n, line: n in TIER_LINES,
    'UI.lua': lambda n, line: 'if p.index > #ns.TIERS then return' in line or 'Button(page, "|cffff7b54Showcase|r"' in line,
}
stray = []
for name in sorted(os.listdir(ROOT)):
    if not name.endswith(('.lua', '.toc')):
        continue
    for n, line in enumerate(open(os.path.join(ROOT, name), encoding='utf-8'), 1):
        low = line.lower()
        if any(c in low for c in STRIPE) and not ALLOWED.get(name, lambda n, line: False)(n, line):
            stray.append('%s:%d' % (name, n))
check(not stray, "no stripe colour outside the quality levels (%s)" % stray)
done()
