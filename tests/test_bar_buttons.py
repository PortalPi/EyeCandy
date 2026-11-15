"""The Peek and Compare buttons on the main window's bottom bar (and the shrunk bar).
Run: python tests/test_bar_buttons.py"""
from lib import boot, chat, check, done

# UIParent, WorldFrame and SetUIVisibility as in test_peek.py, set up before the addon loads.
# Each frame remembers its last anchor, and GetText returns what SetText stored.
PRE = """
local cf = CreateFrame
function CreateFrame(kind, name, parent, template) local f = cf(kind, name, parent, template); f.parent = parent; return f end
UIParent = CreateFrame("Frame", "UIParent"); UIParent.shown = true
WorldFrame = CreateFrame("Frame", "WorldFrame"); WorldFrame.shown = true
function SetUIVisibility(v) UIParent.shown = v and true or false; if v and UIParent.hooks.OnShow then UIParent.hooks.OnShow(UIParent) end end
local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
mt.__index = function(t, k)
  if k == "GetText" then return function(self) return self.text end end
  if k == "SetPoint" then return function(self, p, rel, rp) self.anchor = { p, rel, rp } end end
  return index(t, k)
end
"""

lua = boot(PRE)
lua.execute('FIRE("PLAYER_LOGIN"); FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}; NS.ToggleMain()')
E, X = lua.eval, lua.execute
M = 'EyeCandyMainFrame'
g = lambda n: E('GetCVar("%s")' % n)

check(E(M + '.peek') is not None and E(M + '.compare') is not None, "the bottom bar has Peek and Compare buttons")
check(E(M + '.compare.anchor[2] == %s.export' % M) and E(M + '.peek.anchor[2] == %s.compare' % M), "on the full window they sit left of Export: Peek, Compare, Export")
check(E(M + '.compare.text') == "Compare", "Compare says Compare when off")

# Peek from its button.
X('%s.peek.scripts.OnClick(%s.peek, "LeftButton")' % (M, M))
check(E('NS.IsPeeking()') == True and E(M + '.shown') == False, "Peek hides the game's UI and the window")
X('EyeCandyPeekFrame.button.scripts.OnClick()')
check(E('NS.IsPeeking()') == False and E(M + '.shown') == True, "Back brings them back")

# Compare with nothing to compare: it says why, once.
X('CHAT = {}; %s.compare.scripts.OnClick(%s.compare, "LeftButton")' % (M, M))
said = chat(lua)
check(E('NS.IsComparing()') == False and not said and "Nothing to compare yet" in E(M + '.barMsg.text'), "with nothing to compare, the button says why above the bar, not in chat")

# Apply a preset, then compare from the button.
X('SlashCmdList.EYECANDY("preset cinematic"); CHAT = {}')
now = g("farclip")
X('%s.compare.scripts.OnClick(%s.compare, "LeftButton")' % (M, M))
check(E('NS.IsComparing()') == True and g("farclip") == "7000", "Compare shows the settings from before")
check(E(M + '.compare.text') == "Show now", "while showing before, the button offers \"Show now\"")
check(E(M + '.titleText.text') == "Eye Candy  |cffffd100Showing: before Cinematic|r", "the title says what is on screen")
X('%s.compare.scripts.OnClick(%s.compare, "LeftButton")' % (M, M))
check(g("farclip") == now and E(M + '.compare.text') == "Show before", "clicking again flips to now, and the button offers \"Show before\"")
check(E(M + '.titleText.text') == "Eye Candy  |cffffd100Showing: now|r", "the title follows the flip")

# Right-click ends compare on now.
X('%s.compare.scripts.OnClick(%s.compare, "LeftButton")' % (M, M))
X('%s.compare.scripts.OnClick(%s.compare, "RightButton")' % (M, M))
check(E('NS.IsComparing()') == False and g("farclip") == now, "right-click ends compare on now")
check(E(M + '.compare.text') == "Compare" and E(M + '.titleText.text') == "Eye Candy  |cffffd100Cinematic|r", "the button and title go back to normal: the title names the preset you are on")
X('CHAT = {}; %s.compare.scripts.OnClick(%s.compare, "RightButton")' % (M, M))
check(chat(lua) == [] and E('NS.IsComparing()') == False, "right-click when not comparing does nothing")

# Shrunk: both stay, next to Apply; the title still says what is on screen.
X('NS.ToggleShrink(); %s.compare.scripts.OnClick(%s.compare, "LeftButton")' % (M, M))
check(E(M + '.compare.shown') is not False and E(M + '.peek.shown') is not False, "Peek and Compare stay on the shrunk bar")
check(E(M + '.compare.anchor[2] == %s.apply' % M) and E(M + '.peek.anchor[2] == %s.compare' % M), "shrunk, they sit right of Apply: Apply, Compare, Peek")
check(E(M + '.titleText.text') == "|cffffd100Showing: before Cinematic|r", "the shrunk bar's title says what is on screen")

# Peek while comparing keeps the comparison; closing the window ends it on now.
X('NS.TogglePeek(); %s.scripts.OnHide(%s)' % (M, M))
check(E('NS.IsComparing()') == True and g("farclip") == "7000", "Peek while comparing keeps showing before")
X('NS.TogglePeek()')
X('UIParent.shown = false; %s.scripts.OnHide(%s); UIParent.shown = true' % (M, M))
check(E('NS.IsComparing()') == True, "Alt+Z (the parent hidden, the window still shown) keeps the comparison")
X('CHAT = {}; %s:Hide(); %s.scripts.OnHide(%s)' % (M, M, M))
check(E('NS.IsComparing()') == False and g("farclip") == now, "closing Eye Candy ends compare on now")
check(any("compare ended" in line for line in chat(lua)), "and says so")
X('SlashCmdList.EYECANDY("")')
check(E('NS.IsShrunk()') == False and E(M + '.compare.anchor[2] == %s.export' % M), "opened again full size, they are back left of Export")

# Compare ending on its own (combat, /ec compare stop) redraws the button and title.
X('%s.compare.scripts.OnClick(%s.compare, "LeftButton"); %s.compare.scripts.OnClick(%s.compare, "LeftButton")' % (M, M, M, M))
check(E(M + '.compare.text') == "Show before", "setup: comparing, showing now")
X('INCOMBAT = true; FIRE("PLAYER_REGEN_DISABLED"); INCOMBAT = false; FIRE("PLAYER_REGEN_ENABLED")')
check(E('NS.IsComparing()') == False, "setup: combat ended the compare")
X('%s.scripts.OnUpdate(%s, 0.02)' % (M, M))
check(E(M + '.compare.text') == "Compare" and E(M + '.titleText.text') == "Eye Candy  |cffffd100Cinematic|r", "after combat ends a compare, the button and title go back to normal")
X('%s.compare.scripts.OnClick(%s.compare, "LeftButton"); SlashCmdList.EYECANDY("compare stop"); %s.scripts.OnUpdate(%s, 0.02)' % (M, M, M, M))
check(E('NS.IsComparing()') == False and E(M + '.compare.text') == "Compare", "/ec compare stop redraws the button too")

# A long label is cut to fit the shrunk bar's title.
X('P = NS.SaveCurrentAsPreset("A really long preset name for raids at night"); SlashCmdList.EYECANDY("preset performance"); NS.ApplyPresetById(P.id)')
X('NS.ToggleShrink(); %s.compare.scripts.OnClick(%s.compare, "LeftButton")' % (M, M))
label = E('NS.CompareLabel()')
check(label.startswith("Showing: before A really long preset name") and len(label) > 40, "setup: a long compare label")
check(E(M + '.titleText.text') == "|cffffd100Showing: before A really long p...|r", "shrunk, the title is the label alone, cut to 32 characters")
X('NS.ToggleShrink()')
check(E(M + '.titleText.text') == "Eye Candy  |cffffd100" + label + "|r", "full size, the whole label shows")
X('NS.StopCompare()')

# Without Peek.lua and Compare.lua, the bar has neither button.
lua2 = boot(PRE)
lua2.execute('NS.TogglePeek = nil; NS.ToggleCompare = nil; FIRE("PLAYER_LOGIN"); NS.ToggleMain(); NS.ToggleShrink(); NS.ToggleShrink()')
check(lua2.eval(M + '.peek') is None and lua2.eval(M + '.compare') is None and lua2.eval(M + '.shown') == True, "without Peek and Compare the window works with neither button")
done()
