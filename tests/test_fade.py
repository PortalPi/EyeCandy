"""The main window fades a little when the mouse is away, and /ec fade turns that off.
Run: python tests/test_fade.py"""
from lib import boot, chat, check, done

PRE = """
local cf = CreateFrame
function CreateFrame(kind, name, parent, template) local f = cf(kind, name, parent, template); f.parent = parent; return f end
local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
MOUSEOVER, FOCUS, MENUOPEN = false, nil, false
mt.__index = function(t, k)
  if k == "SetAlpha" then return function(self, a) self.alpha = a end end
  if k == "GetAlpha" then return function(self) return self.alpha or 1 end end
  if k == "IsMouseOver" then return function(self) return MOUSEOVER end end
  if k == "GetParent" then return function(self) return self.parent end end
  return index(t, k)
end
function GetCurrentKeyBoardFocus() return FOCUS end
Menu = { GetManager = function() return { IsAnyMenuOpen = function() return MENUOPEN end } end }
CHATBOX = CreateFrame("EditBox", "ChatFrame1EditBox")
function TICK(n, dt) for i = 1, n do EyeCandyMainFrame.scripts.OnUpdate(EyeCandyMainFrame, dt or 0.1) end end
"""

lua = boot()
lua.execute(PRE)
lua.execute('FIRE("PLAYER_LOGIN"); CHAT = {}; NS.ToggleMain(); EyeCandyMainFrame.scripts.OnShow(EyeCandyMainFrame)')
E, X = lua.eval, lua.execute
M = 'EyeCandyMainFrame'
a = lambda: E(M + '.alpha')

X('TICK(5)')
check(a() == 1, "half a second away: no fade yet")
X('TICK(10)')
check(abs(a() - 0.7) < 1e-9, "after a second away the window fades to 70%")
X('MOUSEOVER = true; TICK(1)')
check(a() == 1, "the mouse back over it: full at once")
X('MOUSEOVER = false; TICK(9)')
check(a() == 1, "the second starts again after the mouse leaves")

# Typing in one of its boxes keeps it full, even with the mouse away.
X('FOCUS = EyeCandySearchBox; TICK(30)')
check(a() == 1, "typing in a box keeps the window full")
X('FOCUS = nil; TICK(30)')
check(abs(a() - 0.7) < 1e-9, "done typing, it fades again")
X('MOUSEOVER = true; TICK(1); MOUSEOVER = false; FOCUS = CHATBOX; TICK(30); FOCUS = nil')
check(abs(a() - 0.7) < 1e-9, "typing in chat (not Eye Candy's box) still lets it fade")

# An open dropdown list sits outside the window; while it is open the window stays full.
X('MOUSEOVER = true; TICK(1); MOUSEOVER = false; MENUOPEN = true; TICK(30)')
check(a() == 1, "with a dropdown list open, the window stays full")
X('MENUOPEN = false; TICK(30)')
check(abs(a() - 0.7) < 1e-9, "the list closed, it fades again")

# Scaling from the grip keeps it full even if the cursor leaves the window.
X('MOUSEOVER = true; TICK(1); MOUSEOVER = false; %s.scaleGrip.left = 10; TICK(30)' % M)
check(a() == 1, "dragging the size grip keeps the window full")
X('%s.scaleGrip.left = nil' % M)

# Reopening starts full.
X('TICK(30); %s.scripts.OnShow(%s)' % (M, M))
check(a() == 1, "reopening the window starts at full")

# /ec fade turns it off, and on again.
X('CHAT = {}; SlashCmdList.EYECANDY("fade")')
check(E('EyeCandyDB.noFade') == True and "no longer fades" in chat(lua)[0], "/ec fade turns fading off, and says so")
X('TICK(30)')
check(a() == 1, "with fading off, the window stays full")
X('SlashCmdList.EYECANDY("fade")')
check(E('EyeCandyDB.noFade') is None and "fades a little" in chat(lua)[0], "/ec fade again turns it back on")
X('TICK(30)')
check(abs(a() - 0.7) < 1e-9, "and it fades again")
done()
