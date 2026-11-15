"""The Compare button on the Peek Back bar (see changes while peeking).
Run alone: python tests/test_peek_bar.py"""
from lib import boot, chat, check, done

# UIParent, WorldFrame and SetUIVisibility as in test_peek.py, set up before the addon loads.
PRE = """
local cf = CreateFrame
function CreateFrame(kind, name, parent, template) local f = cf(kind, name, parent, template); f.parent = parent; return f end
UIParent = CreateFrame("Frame", "UIParent"); UIParent.shown = true
WorldFrame = CreateFrame("Frame", "WorldFrame"); WorldFrame.shown = true
function SetUIVisibility(v) UIParent.shown = v and true or false; if v and UIParent.hooks.OnShow then UIParent.hooks.OnShow(UIParent) end end
"""
BAR = 'EyeCandyPeekFrame'


def start(extra=""):
    lua = boot(PRE + extra)
    lua.execute('FIRE("PLAYER_LOGIN"); FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}')
    return lua


lua = start()
E, X = lua.eval, lua.execute
g = lambda n: E('GetCVar("%s")' % n)
click = lambda: X('%s.compare.scripts.OnClick(%s.compare)' % (BAR, BAR))
X('NS.ToggleMain()')

# Nothing to compare: the button says why, once.
X('NS.TogglePeek()')
check(E(BAR + '.compare') is not None and E(BAR + '.compare.parent == ' + BAR), "the Back bar has a Compare button")
check(E(BAR + '.compare.text') == "Show before" and (E(BAR + '.label.text') or "") == "", "off: it offers \"Show before\" and the label is empty")
X('CHAT = {}')
click()
said = chat(lua)
check(E('NS.IsComparing()') == False and len(said) == 1 and "Nothing to compare yet" in said[0], "with nothing to compare, it says why, once")
X('NS.TogglePeek()')

# After a preset, clicks flip and the button and label follow.
X('SlashCmdList.EYECANDY("preset cinematic"); CHAT = {}')
now = g("farclip")
X('NS.TogglePeek()')
check(E(BAR + '.compare.text') == "Show before", "peek starts with \"Show before\"")
click()
check(E('NS.IsComparing()') == True and g("farclip") == "7000" and now != "7000", "a click shows before")
check(E(BAR + '.compare.text') == "Show now" and E(BAR + '.label.text') == "Showing: before Cinematic", "the button offers \"Show now\" and the label names what is on screen")
click()
check(g("farclip") == now and E(BAR + '.compare.text') == "Show before" and E(BAR + '.label.text') == "Showing: now", "a second click shows now, the button offers \"Show before\"")
click()
check(g("farclip") == "7000", "and flips again")
check(E('NS.IsPeeking()') == True and E('NS.IsComparing()') == True, "flipping keeps the peek going")

# Combat ending a compare redraws the bar and the main window.
X('RCALLS = 0; local r = NS.RefreshUI; NS.RefreshUI = function(...) RCALLS = RCALLS + 1; if r then return r(...) end end')
X('FIRE("PLAYER_REGEN_DISABLED")')
check(E('NS.IsComparing()') == False and g("farclip") == now, "combat ends compare on now")
check(E('RCALLS') >= 1, "the main window is told to redraw")
check(E(BAR + '.compare.text') == "Show before" and (E(BAR + '.label.text') or "") == "", "the bar's button and label go back to normal")
X('NS.TogglePeek()') if E('NS.IsPeeking()') else None

# Ending on its own while showing now (the state clears without a Show call) still redraws.
X('NS.TogglePeek(); NS.ToggleCompare(); NS.ToggleCompare(); RCALLS = 0')
X('NS.StopCompare()')
check(E('RCALLS') >= 1 and E(BAR + '.compare.text') == "Show before" and (E(BAR + '.label.text') or "") == "", "StopCompare while showing now redraws the main window and bar")
X('NS.ToggleCompare(); RCALLS = 0; NS.CreateBackup("manual", "Mine")')
check(E('NS.IsComparing()') == False and E('RCALLS') >= 1 and (E(BAR + '.label.text') or "") == "", "a backup while showing before ends compare and redraws")

# Back still ends the peek, with compare running.
X('NS.ToggleCompare()')
check(E('NS.IsComparing()') == True, "setup: comparing")
X('%s.button.scripts.OnClick()' % BAR)
check(E('NS.IsPeeking()') == False and E('UIParent:IsShown()') and E('NS.IsComparing()') == True, "Back ends the peek and keeps the compare running")
X('NS.StopCompare()')

# Esc (UIParent shown by the game) still ends it.
X('NS.TogglePeek(); SetUIVisibility(true)')
check(E('NS.IsPeeking()') == False, "Esc still ends the peek")

# A long preset name is cut to fit the bar's one-line label.
X('P = NS.SaveCurrentAsPreset("A really long preset name for raids at night"); SlashCmdList.EYECANDY("preset performance"); NS.ApplyPresetById(P.id)')
X('NS.TogglePeek(); %s.compare.scripts.OnClick()' % BAR)
said = E(BAR + '.label.text') or ""
check(said.startswith("Showing: before A really long") and len(said) == 42 and said.endswith("..."), "a long label is cut to 39 characters and ...")
X('NS.StopCompare(); NS.TogglePeek()')

# Without Compare.lua the bar has no such button and Peek works.
lua = boot(PRE + 'NS.ToggleCompare = nil')
E, X = lua.eval, lua.execute
X('NS.ToggleCompare = nil; FIRE("PLAYER_LOGIN"); FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}')
check(E('NS.TogglePeek()') == True and E('NS.IsPeeking()'), "without Compare, Peek starts")
check(E(BAR + '.compare') is None and E(BAR + '.label') is None, "and the bar has no Compare button")
X('%s.button.scripts.OnClick()' % BAR)
check(E('NS.IsPeeking()') == False and E('UIParent:IsShown()'), "and Back ends it")

done()
