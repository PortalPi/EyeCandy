"""The On now card: with no preset it says only what is true (Back shows only after a preset was
applied), and its right edge lines up with the rows under it. Run: python tests/test_card.py"""
from lib import boot, check, done, GEO

lua = boot()
E, X = lua.eval, lua.execute
X(GEO)
X("""
for k, v in pairs({ bloomUserMult = "1", cameraFov = "90", Contrast = "57", Brightness = "46" }) do C_CVar.RegisterCVar(k, v) end
""")
X('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}; SlashCmdList.EYECANDY("")')
P = 'EyeCandyMainFrame.pages.presets'

# (a) No preset yet.
text = E(P + '.card.detail.text')
check(E(P + '.backButton.shown') == False, "before any preset there is no Back button")
check("Back" not in text and "undo" not in text, "so the card does not mention Back or undo (%r)" % text)
check(text == "Pick one below. A preset applies when you press Apply on it.", "it says only what a row does, so it stays true while the city switch or Autotune runs")

# After a preset: Back shows, and the card says what is on.
X('NS.ApplyPresetById("tier1"); NS.RefreshUI()')
check(E(P + '.backButton.shown') == True and E(P + '.card.name.text') == "Performance", "after Performance, Back shows and the card names it")

# A preset deleted while Back still shows: still nothing false on the card.
X('MINE = NS.SaveCurrentAsPreset("Mine"); NS.ApplyPresetById(MINE.id); NS.DeletePreset(MINE.id); NS.RefreshUI()')
text = E(P + '.card.detail.text')
check(E(P + '.card.name.text') != "Mine" and "Back to before undoes it" not in text, "no stale promise on the card after the preset is deleted (%r)" % text)

# (b) One right edge: the card is as wide as the rows, from the same left edge.
check(E(P + '.card.geo.w') == E('NS.ROW_W'), "the card is ROW_W wide (%s)" % E(P + '.card.geo.w'))
check(E(P + '.rows[1].geo.w') == E(P + '.card.geo.w'), "the rows under it are the same width")
done()
