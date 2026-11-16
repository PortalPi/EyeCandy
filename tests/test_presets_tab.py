"""The Presets tab: the "On now" card, the gold row for the preset you are on, section headings,
one Apply and a "..." menu per row, the Import strip, and what Back on one of today's steps says
on the card (tests/test_back_history.py has the Today list itself).
Run: python tests/test_presets_tab.py"""
from lib import boot, check, done

REG = """
for k, v in pairs({ bloomUserMult = "1", cameraFov = "90", Contrast = "57", Brightness = "46" }) do C_CVar.RegisterCVar(k, v) end
local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
mt.__index = function(t, k) if k == "GetText" then return function(self) return self.text end end return index(t, k) end
"""

lua = boot()
lua.execute(REG)
lua.execute('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}; SlashCmdList.EYECANDY("")')
E, X = lua.eval, lua.execute
P = 'EyeCandyMainFrame.pages.presets'
M = 'EyeCandyMainFrame'
TICK = lambda: X('for i = 1, 11 do %s.scripts.OnUpdate(%s, 0.1) end' % (M, M))


def headers():
    n = E('#%s.headers' % P)
    return [E('%s.headers[%d].label.text' % (P, i)) for i in range(1, n + 1) if E('%s.headers[%d].shown' % (P, i))]


def row(name):
    n = E('#%s.rows' % P)
    for i in range(1, n + 1):
        if E('%s.rows[%d].p.name' % (P, i)) == name and E('%s.rows[%d].shown' % (P, i)):
            return '%s.rows[%d]' % (P, i)


def shown_rows():
    n = E('#%s.rows' % P)
    return [E('%s.rows[%d].p.name' % (P, i)) for i in range(1, n + 1) if E('%s.rows[%d].shown' % (P, i))]


def apply(name):
    r = row(name)
    X('%s.apply.scripts.OnClick(%s.apply)' % (r, r))


# Headings: your presets first, then the built-ins, each large with a gold rule under it.
hs = headers()
check(hs == ["Your presets", "Quality levels", "Looks", "Situations"], "sections: Your presets, Quality levels, Looks, Situations (%s)" % hs)
src =open(__file__.replace('tests\\test_presets_tab.py', 'EyeCandy\\UI.lua').replace('tests/test_presets_tab.py', 'EyeCandy/UI.lua'), encoding='utf-8').read()
check('f.label = Label(f, text, "GameFontNormalLarge")' in src and 'f.rule:SetColorTexture(1, 0.82, 0, 0.35)' in src and 'SectionHeader' not in src, "a section heading is ns.Header: the large font with a gold rule under it (tests/test_preset_headings.py has more)")
check(E(P + '.headers[2].note.text') == "Every system at one level.", "a heading's note sits under its rule")
# Space: a gap between sections, and between rows.
check('ROW_H, ROW_GAP, GROUP_GAP = 34, 4, 24' in src, "rows are 34 tall with a 4 gap; sections have 24 more above them")

# Every row: a name, a one-line summary, one Apply and a "..." button. No other buttons.
r = row("High")
check(E(r + '.name.text') == "High" and E(r + '.line.text') == "Sharp and smooth on a decent PC.", "a quality level shows its name and a plain line")
check(E(r + '.apply.shown') != False and E(r + '.more.text') == "...", "a row has Apply and a ... button")
check(E(r + '.buttons') is None, "no row of five buttons any more")
r = row("Raid & PvP")
check(E(r + '.line.text') == "Clear and steady for big fights.", "a Situation's line is the first sentence of its description (%r)" % E(r + '.line.text'))

# No preset yet: the card says so, and no row is gold.
check(E(P + '.card.name.text') == "|cff9d9d9dNo preset yet|r", "before any preset the card says No preset yet, in grey")
check(not any(E('%s.rows[%d].on' % (P, i)) for i in range(1, E('#%s.rows' % P) + 1)), "no row is marked on before any preset")
check("Eye Candy  |cffffd100" not in (E(M + '.titleText.text') or ""), "the title names no preset yet")

# Apply Moody from its row: the card, the row and the title all say Moody.
apply("Moody")
check(E(P + '.card.name.text') == "Moody" and E(P + '.card.detail.text') == "Look.", "after Moody the card says Moody, a Look")
r = row("Moody")
check(E(r + '.on') == True and E(r + '.tag.text') == "|cffffd100On now|r", "the Moody row is gold and tagged On now")
check(E(r + '.apply.shown') == False, "the row you are on has no Apply (nothing to apply)")
check(E(M + '.titleText.text') == "Eye Candy  |cffffd100Moody|r", "the title bar names Moody, on every tab")
check(E(row("High") + '.on') == False, "other rows are not gold")

# A setting changed since: the card counts it, the row offers Apply again, within a second.
was = E('GetCVar("farclip")')
X('SetCVar("farclip", "%s")' % ("1000" if was != "1000" else "2000"))
TICK()
check("1 setting changed since you applied it." in E(P + '.card.detail.text'), "a change shows on the card within a second (%r)" % E(P + '.card.detail.text'))
r = row("Moody")
check("(1 changed)" in E(r + '.tag.text') and E(r + '.apply.shown') == True, "the row says 1 changed and offers Apply to put it back")
X('SetCVar("farclip", "%s")' % was)
TICK()
check(E(P + '.card.detail.text') == "Look.", "putting it back clears the count")

# Your own preset can be the one you are on.
X('MINE = NS.SaveCurrentAsPreset("Night raid"); NS.RefreshUI()')
apply("Night raid")
check(E(P + '.card.name.text') == "Night raid" and E(P + '.card.detail.text') == "Your preset.", "your own preset shows on the card")
check(E(row("Night raid") + '.on') == True and E(row("Moody") + '.on') == False, "and its row is the gold one")
check(shown_rows()[0] == "Night raid", "your presets are listed first")

# The ... menu: built-ins share and duplicate; yours also rename and delete. Right-click opens it too.
items = lambda pid: [E('NS.PresetMenuItems(NS.FindPreset("%s"))[%d][1]' % (pid, i)) for i in range(1, E('#NS.PresetMenuItems(NS.FindPreset("%s"))' % pid) + 1)]
check(items("tier3") == ["share", "duplicate"], "a built-in's menu: Share, Duplicate")
check(items(E('MINE.id')) == ["share", "duplicate", "rename", "delete"], "your preset's menu adds Rename and Delete")
r = row("High")
X('%s.more.scripts.OnClick(%s.more)' % (r, r))
check(E('EyeCandyPresetMenu.shown') == True and E('EyeCandyPresetMenu.buttons[1].text') == "Share", "... opens the menu (the stand-in list when the game's menu isn't there)")
X('CHAT = {}; EyeCandyPresetMenu.buttons[2].scripts.OnClick(EyeCandyPresetMenu.buttons[2])')
check(row("High (2)") is not None and E('EyeCandyPresetMenu.shown') == False, "Duplicate from the menu makes High (2) and closes the menu")
r = row("High (2)")
X('%s.scripts.OnClick(%s, "RightButton")' % (r, r))
check(E('EyeCandyPresetMenu.shown') == True and E('#EyeCandyPresetMenu.buttons') >= 4 and E('EyeCandyPresetMenu.buttons[4].shown') == True, "right-clicking your preset's row opens its menu, with Delete")
X('EyeCandyPresetMenu:Hide()')
X('MENUS = {}; MenuUtil = { CreateContextMenu = function(owner, gen) local root = { items = {} }; function root:CreateTitle(t) self.title = t end; function root:CreateButton(t, f) self.items[#self.items + 1] = { t, f } end; gen(owner, root); MENUS[#MENUS + 1] = root end }')
r = row("Painterly")
X('%s.more.scripts.OnClick(%s.more)' % (r, r))
check(E('MENUS[1].title') == "Painterly" and E('MENUS[1].items[1][1]') == "Share" and E('#MENUS[1].items') == 2, "with the game's menu, ... opens it with the preset's name and items")
X('MenuUtil = nil')

# Import strip: always on the tab, under your presets. A good code saves a new preset, marked New,
# and applies nothing.
check(E(P + '.strip.shown') == True and E(P + '.strip.title.text') == "Import a preset", "the Import strip is on the tab")
code = E('NS.ExportPreset("look:crisp")')
X('NS.ApplyPresetById("tier1")')
X('%s.strip.box.text = [[%s]]; NS.UpdateImportStrip(%s)' % (P, code, P))
res = E(P + '.strip.result.text')
check("Crisp" in res and "Changes" in res and "Replace it, or keep both" in res, "pasting a code shows what it is (%r)" % res)
check(E(P + '.strip.keep.shown') == True and E(P + '.strip.replace.shown') == True and E(P + '.strip.import.shown') == False, "a name you already have offers Keep both or Replace")
farclip = E('GetCVar("farclip")')
X('%s.strip.keep.scripts.OnClick(%s.strip.keep)' % (P, P))
check(row("Crisp (2)") is not None and E(row("Crisp (2)") + '.tag.text') == "|cff7cff7cNew|r", "the import is saved as Crisp (2) in Your presets, marked New")
check(E('GetCVar("farclip")') == farclip and E(P + '.card.name.text') == "Performance", "importing applies nothing: you are still on Performance")
check("Saved \"Crisp (2)\" in Your presets" in E(P + '.strip.result.text') and E(P + '.strip.box.text') == "", "the strip says where it went and clears the box")
X('%s.strip.box.text = "hello"; NS.UpdateImportStrip(%s)' % (P, P))
check("Can't read this code." in E(P + '.strip.result.text') and E(P + '.strip.import.shown') == False, "a bad code can't be imported (no Import button)")
X('%s.strip.box.text = ""; NS.UpdateImportStrip(%s)' % (P, P))
check(E(P + '.strip.result.text') == "", "clearing the box clears the message")
check(E(P + '.scrolledTo') == max(0, E(row("Crisp (2)") + '.top') - 36), "importing scrolls the list to the new row")
# New lasts until you apply something or leave the tab.
apply("High")
check(E(P + '.newId') is None and E(row("Crisp (2)") + '.tag.text') == "", "applying a preset clears New")
X('%s.newId = "x"; %s.importMsg = "m"; %s.hooks.OnHide(%s)' % (P, P, P, P))
check(E(P + '.newId') is None and E(P + '.importMsg') is None, "leaving the tab clears New and the import message")
X('NS.ApplyPresetById("tier1")')

# Long names are cut, never wrapped, on the card and in a row.
X('LONG = NS.SaveCurrentAsPreset("A very long preset name that goes on and"); NS.ApplyPresetById(LONG.id)')
check(E(P + '.card.name.text') == "A very long preset name tha..." and E(row("A very long preset name that goes on and") + '.name.text') == "A very long preset name t...", "a long name is cut with ... on the card and in its row")
check('c.name:SetWordWrap(false)' in src and 'c.detail:SetWordWrap(false)' in src and 'c.detail:SetPoint("RIGHT", c, "RIGHT", -16, 0)' in src, "the card's name and detail run to its right edge and never wrap")
X('NS.DeletePreset(LONG.id); NS.ApplyPresetById("tier1")')
check(row("A very long preset name that goes on and") is None, "a deleted preset's row is hidden when the list gets shorter")

# Under Capital city: a tick box to switch it in cities by itself.
box = P + '.cityBox'
check(E(box + '.shown') == True and E(box + '.text.text') == "Lower settings in capital cities", "a city tick box sits under Capital city")
X('TIP = {}; GameTooltip.AddLine = function(self, t) TIP[#TIP + 1] = t end; %s.scripts.OnEnter(%s)' % (box, box))
check(E('TIP[2]') == "Lowers view distance, environment detail, fog and far-away character detail. Only where yours are higher, and never in a fight.", "the city box's tooltip says what it lowers and when")
X('GameTooltip.AddLine = nil; %s.scripts.OnClick(%s)' % (box, box))
check(E('NS.IsAutoSituationOn("city")') == True, "ticking the box turns the city switch on")
X('NS.SetAutoSituation("city", false)')

# Back on one of today's steps (its row in the Today list): click it, then Back on the question.
A = 'EyeCandyAskFrame'


def back_newest():
    n = E('#(%s.stepRows or {})' % P)
    r = next('%s.stepRows[%d]' % (P, i) for i in range(1, n + 1) if E('%s.stepRows[%d].shown' % (P, i)))
    X('%s.back.scripts.OnClick(%s.back); %s.accept.scripts.OnClick(%s.accept)' % (r, r, A, A))


check(E(P + '.backButton') is None, "the card has no Back button: Back lives on today's steps")
X('NS.DeletePreset(MINE.id); NS.RefreshUI()')
X('CHAT = {}')
weather = E('GetCVar("weatherDensity")')
apply("Raid & PvP")
check(E('NS.BackSteps()[1].name') == "Raid & PvP", "applying Raid & PvP makes it today's newest step")
check(E(P + '.card.name.text') == "Raid & PvP" and E(P + '.card.detail.text') == "Situation.", "the card calls a Situation a Situation")
check(E('GetCVar("weatherDensity")') == "0", "Raid & PvP set no weather")

# Back on it: the settings from before come back, and the card says so.
back_newest()
check(weather != "0" and E('GetCVar("weatherDensity")') == weather, "Back puts the settings back as they were before Raid & PvP")
note = E(P + '.card.note.text')
check(note.startswith("|cff7cff7cBack to before Raid & PvP: ") and note.endswith(" put back.|r"), "the card says what Back put back, in green (%r)" % note)
check(not any("Back to before" in x or "estored" in x for x in E('CHAT').values()), "and Back from the window prints nothing to chat")
X('NS.RefreshUI(); NS.MainTick(%s, NS.BACK_CHECK_EVERY)' % M)
check(E(P + '.card.note.text') == note, "Back's result stays while nothing it was about changes")
X('%s.hooks.OnHide(%s); NS.RefreshUI()' % (P, P))
check(E(P + '.card.note.text') == "", "leaving the tab clears Back's result")

# What is running on your settings shows on the card and in the title.
X('NS.AutotuneNote = function() return "Autotune is testing settings" end; NS.RefreshUI()')
check(E(P + '.card.note.text') == "|cffffd100Autotune is testing settings|r", "the card shows what Autotune is doing")
check("|cffffd100Autotune is testing settings|r" in E(M + '.titleText.text'), "and so does the title (%r)" % E(M + '.titleText.text'))
X('NS.AutotuneNote = nil; REAL_ASN = NS.ActiveSituationName; NS.ActiveSituationName = function() return "Capital city" end; NS.RefreshUI()')
check(E(P + '.card.note.text') == "|cffffd100In a city: some settings lowered|r" and "In a city: some settings lowered" in E(M + '.titleText.text'), "in a city the card and the title say so")
X('NS.ActiveSituationName = REAL_ASN; NS.RefreshUI()')
check(E(P + '.card.note.text') == "" and "In a city" not in E(M + '.titleText.text'), "out of the city the note goes")

# A red line goes once what it said stops being true: a fight ends, or Autotune takes the line.
apply("Laptop")
X('INCOMBAT = true')
back_newest()
refused = E(P + '.card.note.text')
check(refused.startswith("|cffff4040") and "combat" in refused, "Back in a fight says why not on the card, in red (%r)" % refused)
X('NS.MainTick(%s, NS.BACK_CHECK_EVERY)' % M)
check(E(P + '.card.note.text') == refused, "the red line stays while the fight goes on")
X('INCOMBAT = false; NS.MainTick(%s, NS.BACK_CHECK_EVERY)' % M)
check(E(P + '.card.note.text') == "", "once the fight is over the red line goes by itself")
X('INCOMBAT = true')
back_newest()
X('NS.AutotuneNote = function() return "Autotune is testing settings" end; NS.RefreshUI()')
check(E(P + '.card.note.text') == "|cffffd100Autotune is testing settings|r", "once Autotune starts, its note takes the line from an old result, fight or not")
X('INCOMBAT = false; NS.AutotuneNote = nil; NS.RefreshUI()')

# A long name is cut by whole characters.
check(E('NS.ShortName("Raid & PvP", 18)') == "Raid & PvP", "a short name is left whole")
check(E('NS.ShortName("My very long preset name here", 18)') == "My very long pres...", "a long name is cut to 18 characters with ...")
cut = E('NS.ShortName("Caf\\195\\169 \\195\\169t\\195\\169 \\195\\169t\\195\\169 \\195\\169t\\195\\169 \\195\\169t\\195\\169", 10)')
check(cut == "Café été ...", "a name with accents is cut between characters, never inside one")

# With no preset on and no steps today, the timed check reads no settings.
X('EyeCandyDB.steps = {}; EyeCandyDB.onPreset = nil; EyeCandyDB.look = nil; NS.RefreshUI(); CALLS = 0; local f = NS.StepsKey; NS.StepsKey = function(...) CALLS = CALLS + 1; return f(...) end; local g = NS.OnPreset; NS.OnPreset = function() CALLS = CALLS + 1; return g() end')
TICK()
check(E('CALLS') == 0, "with no preset on and nothing to go back to, the timed check is skipped")

# No tooltip runs off the window's right edge: the row's buttons open theirs to the left.
check(src.count('"ANCHOR_LEFT")') >= 6 and 'GameTooltip:SetOwner(self, "ANCHOR_CURSOR")' in src, "row buttons anchor tooltips to the left, rows at the cursor")

# Without today's steps (an older Steps.lua missing), the tab still builds, with no Today list.
lua2 = boot()
lua2.execute(REG)
lua2.execute('NS.StepEntries = nil; FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); NS.ApplyPresetById("tier1"); SlashCmdList.EYECANDY("")')
check(lua2.eval('EyeCandyMainFrame.pages.presets.usesList') == True and lua2.eval('EyeCandyMainFrame.pages.presets.stepRows') is None, "without today's steps the Presets tab builds with no Today rows")
done()
