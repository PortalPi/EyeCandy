"""Shared test helpers, so each change can run only its own checks.

Use from a new file such as tests/test_presets.py:

    from lib import boot, chat, check, done
    lua = boot()
    check(..., "what this proves")
    done()

Run it with `python tests/test_presets.py`. Files load in the order the .toc lists them,
so a new addon file is picked up as soon as it is in EyeCandy.toc.
tests/run.py is the older full suite; it is not run per change.
"""
import lupa.lua51 as L, os, sys

base = os.path.dirname(os.path.abspath(__file__)) + os.sep
addon = os.path.join(base, '..', 'EyeCandy') + os.sep


def toc_files():
    files = []
    for line in open(addon + 'EyeCandy.toc', encoding='utf-8'):
        line = line.strip()
        if line and not line.startswith('#') and line.endswith('.lua'):
            files.append(line)
    return files


def boot(svdb=None, mirror=None):
    lua = L.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(open(base + 'harness.lua', encoding='utf-8').read())
    lua.execute("""ALLFRAMES = {}; local cf = CreateFrame
      function CreateFrame(...) local f = cf(...); ALLFRAMES[#ALLFRAMES+1] = f; return f end
      function FIRE(ev, ...) for _, f in ipairs(ALLFRAMES) do if f.scripts.OnEvent then f.scripts.OnEvent(f, ev, ...) end end end
      function RUNTIMERS() local t = TIMERS; TIMERS = {}; for _, f in ipairs(t) do f() end end
      NS = {}""")
    if svdb:
        lua.execute(svdb)
    if mirror:
        lua.execute('C_CVar.RegisterCVar("eyeCandyMirror", ""); C_CVar.SetCVar("eyeCandyMirror", %r)' % mirror)
    loader = lua.eval('function(src, name) local f, e = loadstring(src, name); if not f then error(e) end; return f end')
    for f in toc_files():
        loader(open(addon + f, encoding='utf-8').read(), f)('EyeCandy', lua.eval('NS'))
    lua.execute('FIRE("ADDON_LOADED", "EyeCandy")')
    return lua


# Frame geometry the harness lacks: size, scale and a TOPLEFT/CENTER anchor, kept per frame in
# frame units, on a 1920 x 1080 UIParent. GetText returns what SetText stored.
# Use: lua.execute(GEO) after boot(), before any window is built.
GEO = """
local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
local SW, SH = 1920, 1080
local function g(self) self.geo = self.geo or { w = 0, h = 0, s = 1 }; return self.geo end
local over = {
  GetText = function(self) return self.text end,
  SetSize = function(self, w, h) local q = g(self); q.w, q.h = w, h end,
  SetScale = function(self, s) g(self).s = s end,
  GetScale = function(self) return g(self).s end,
  ClearAllPoints = function(self) local q = g(self); q.l, q.t = nil, nil end,
  SetPoint = function(self, p, rel, rp, x, y)
    local q = g(self)
    if p == "CENTER" and rel == nil then q.l = (SW / q.s - q.w) / 2; q.t = (SH / q.s + q.h) / 2
    elseif p == "TOPLEFT" and rel == UIParent and rp == "BOTTOMLEFT" then q.l, q.t = x, y end
  end,
  GetLeft = function(self) return g(self).l end,
  GetTop = function(self) return g(self).t end,
  SetUserPlaced = function(self, v) self.userPlaced = v end,
}
mt.__index = function(t, k) if over[k] then return over[k] end return index(t, k) end
UIParent = setmetatable({ scripts = {}, hooks = {} }, mt)
UIParent.GetEffectiveScale = function() return 1 end
CURSOR = { 0, 0 }
function GetCursorPosition() return CURSOR[1], CURSOR[2] end
-- The top-left corner in UIParent units.
function CORNER(f) local q = f.geo; return q.l * q.s, q.t * q.s end
"""


def near(a, b):
    return a is not None and b is not None and abs(a - b) < 1e-6


def chat(lua):
    out = list(lua.eval('CHAT').values())
    lua.execute('CHAT = {}')
    return out


_ok = True


def check(cond, msg):
    global _ok
    print(("PASS " if cond else "FAIL ") + msg)
    _ok = _ok and bool(cond)


def done():
    print("\nALL PASS" if _ok else "\nSOME FAILED")
    sys.exit(0 if _ok else 1)
