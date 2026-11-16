"""The patch warning (PatchWatch.lua): at logout Eye Candy keeps a copy of your settings, and at the next
login it says which ones changed while the game was closed, with Put them back and Keep the game's.

Run alone: python tests/test_patch_watch.py
"""
from lib import boot, chat, check, done

# Turns EyeCandyDB into Lua source, so a new session (a new Lua state) can load it like saved data.
SER = """
function SER(v)
  local t = type(v)
  if t == "string" then return string.format("%q", v) end
  if t == "number" or t == "boolean" then return tostring(v) end
  if t ~= "table" then return "nil" end
  local out = {}
  for k, x in pairs(v) do out[#out + 1] = "[" .. SER(k) .. "]=" .. SER(x) end
  return "{" .. table.concat(out, ",") .. "}"
end
"""

# Dials the stub client doesn't register by itself, so the Standard and Hidden lists exist.
STUBS = """
for k, v in pairs({ bloomUserMult = "1", cameraFov = "90", Contrast = "57", Brightness = "46" }) do C_CVar.RegisterCVar(k, v) end
"""


def session(svdb=None, before=None, login=True):
    """A game session: load, set the values the game starts with, log in, let the timers run."""
    lua = boot(svdb)
    lua.execute(SER + STUBS)
    if before:
        lua.execute(before)
    lua.execute('FIRE("PLAYER_ENTERING_WORLD", %s, %s); RUNTIMERS(); RUNTIMERS()' % (
        'true' if login else 'false', 'false' if login else 'true'))
    return lua


def logout(lua):
    lua.execute('FIRE("PLAYER_LOGOUT")')
    return 'EyeCandyDB = ' + lua.eval('SER(EyeCandyDB)')


def frame(lua):
    return lua.eval('EyeCandyPatchFrame')


def shown(lua):
    f = frame(lua)
    return bool(f is not None and f.shown)


def lines(lua):
    f = frame(lua)
    return [l.text for l in f.lines.values() if l.shown]


ev = lambda lua, s: lua.eval(s)
g = lambda lua, n: lua.eval('GetCVar("%s")' % n)

# Pure logic first: what counts as a change.
lua = session()
diff = lua.eval("""function(old, now, seen)
  local show, all = NS.PatchWatch.Diff(old, now, { "a", "b", "c", "d", "a" }, seen)
  local out = {}
  for _, c in ipairs(show) do out[#out + 1] = c.cvar .. "=" .. c.was .. ">" .. c.now end
  local n = 0
  for _ in pairs(all) do n = n + 1 end
  return table.concat(out, ","), n
end""")
T = lua.table_from
shows, n = diff(T({'a': '1', 'b': '2', 'c': '3'}), T({'a': '1', 'b': '5', 'c': '3.0', 'd': '4'}), None)
check(shows == "b=2>5" and n == 1, "only a real change counts: 3 and 3.0 are the same, a new setting is not a change")
shows, n = diff(T({'a': '1', 'b': '2'}), T({'a': '9', 'b': '5'}), T({'b': T({'was': '2', 'now': '5'})}))
check(shows == "a=1>9" and n == 2, "a change shown last time, the same again, is not shown (something rewrites it at every start)")
shows, _ = diff(T({'b': '2'}), T({'b': '6'}), T({'b': T({'was': '2', 'now': '5'})}))
check(shows == "b=2>6", "a different change to the same setting is shown")
shows, _ = diff(T({'a': '1'}), T({'a': '2'}), None)
check(shows == "a=1>2", "a setting listed twice shows once")

# First login after install: nothing to compare with, so nothing shows.
check(not shown(lua), "first login after install: no window")
check(ev(lua, 'EyeCandyDB.patchWatch == nil or EyeCandyDB.patchWatch.snap == nil'), "no copy before the first logout")

# A setting changed during play is in the logout copy, so it never counts.
lua.execute('SetCVar("graphicsSSAO", "2")')
db = logout(lua)
check(ev(lua, 'EyeCandyDB.patchWatch.snap.values.graphicsSSAO') == "2", "logout keeps a copy of your settings")
lua2 = session(db, 'SetCVar("graphicsSSAO", "2")')
check(not shown(lua2), "nothing changed while the game was closed: no window, nothing in chat")
check(not any("changed" in l for l in chat(lua2)), "and no chat line")

# The game changes settings while it is closed: one window, how many, a short list.
backups = ev(lua2, '#NS.ListBackups()')
db = logout(lua2)
patch = 'SetCVar("graphicsSSAO", "2"); SetCVar("RenderScale", "1"); SetCVar("graphicsViewDistance", "5")'
lua3 = session(db, 'EyeCandyDB.patchWatch.snap.values.RenderScale = "1.5";' + patch)
check(shown(lua3), "two settings changed while the game was closed: the window shows")
head = frame(lua3).head.text
check(head == "The game changed 2 settings since you last played. Put them back?", "it says how many: " + head)
ls = lines(lua3)
check("Render Scale: was 150%, now 100%" in ls, "render scale shows as percent, was and now: %s" % ls)
check(any(l.startswith("View Distance: was 10, now 6") for l in ls), "view distance shows as the game's menu shows it (1 to 10)")
check(frame(lua3).back.text == "Put them back" and frame(lua3).keep.text == "Keep the game's", "two buttons: Put them back, Keep the game's")
check(frame(lua3).back.shown is not False and frame(lua3).keep.shown is not False, "both buttons show")
check("EyeCandyPatchFrame" in list(ev(lua3, 'NS.PEEK_WINDOWS').values()), "Peek hides it like Eye Candy's other windows")
check(ev(lua3, '(function() for _, n in ipairs(UISpecialFrames) do if n == "EyeCandyPatchFrame" then return true end end end)()'), "Esc closes it")

# Put them back: sets them, reads them back, says any the game refused. No backup. Render scale is
# held at 100% (the game's top since its 14 November 2026 patch).
lua3.execute('function GetMaxRenderScale() return 1 end')
nb = ev(lua3, '#NS.ListBackups()')
frame(lua3).back.scripts.OnClick(frame(lua3).back)
check(g(lua3, "graphicsViewDistance") == "9", "Put them back sets view distance back")
check(g(lua3, "RenderScale") == "1", "render scale over the game's top is not forced")
check(frame(lua3).result.text == "Put back 1 setting.", "it says how many went back: %s" % frame(lua3).result.text)
check(frame(lua3).refused.text == "|cffff4040The game kept Render Scale at 100%.|r", "and, in red, the one the game refused: %s" % frame(lua3).refused.text)
check(ev(lua3, '#NS.ListBackups()') == nb, "Put them back takes no backup")
check(frame(lua3).back.shown is False and frame(lua3).keep.shown is False and frame(lua3).close.shown, "after it, only Close shows")

# The next logout keeps what is on now, so the refused one does not come back.
db = logout(lua3)
lua4 = session(db, 'SetCVar("graphicsSSAO", "2")')
check(not shown(lua4), "next login: nothing new, no window")

# Keep the game's changes nothing and closes.
lua5 = session(db, 'SetCVar("graphicsSSAO", "2"); SetCVar("graphicsShadowQuality", "1")')
check(shown(lua5) and frame(lua5).head.text.startswith("The game changed 1 setting since you last played. Put it back?"), "one setting: Put it back? (%s)" % frame(lua5).head.text)
check(frame(lua5).back.text == "Put it back", "one setting: the button says Put it back")
frame(lua5).keep.scripts.OnClick(frame(lua5).keep)
check(not shown(lua5) and g(lua5, "graphicsShadowQuality") == "1", "Keep the game's closes and changes nothing")
db_kept = logout(lua5)
lua6 = session(db_kept, 'SetCVar("graphicsSSAO", "2"); SetCVar("graphicsShadowQuality", "1")')
check(not shown(lua6), "after Keep the game's, the next login asks nothing")

# Something rewrites a setting at every start (the game or another addon): shown once, then never again.
lua7 = session(db, 'SetCVar("graphicsSSAO", "2"); SetCVar("graphicsShadowQuality", "1")')
frame(lua7).back.scripts.OnClick(frame(lua7).back)
check(g(lua7, "graphicsShadowQuality") == "5", "put back")
db7 = logout(lua7)
lua8 = session(db7, 'SetCVar("graphicsSSAO", "2"); SetCVar("graphicsShadowQuality", "1")')
check(not shown(lua8), "the same change at the next start: not shown again")

# In a fight: the check waits, and Put them back waits too. Nothing changes in combat.
lua9 = session(db, 'SetCVar("graphicsSSAO", "2"); SetCVar("graphicsShadowQuality", "1"); INCOMBAT = true')
check(not shown(lua9), "in a fight at login: the window waits")
lua9.execute('INCOMBAT = false; FIRE("PLAYER_REGEN_ENABLED"); RUNTIMERS()')
check(shown(lua9), "after the fight: the window shows")
lua9.execute('INCOMBAT = true')
frame(lua9).back.scripts.OnClick(frame(lua9).back)
check(g(lua9, "graphicsShadowQuality") == "1", "Put them back in a fight changes nothing")
check(frame(lua9).result.text == "|cff9d9d9dWaiting for the fight to end. Then it goes back.|r", "it says it is waiting, in grey: %s" % frame(lua9).result.text)
lua9.execute('INCOMBAT = false; FIRE("PLAYER_REGEN_ENABLED"); RUNTIMERS()')
check(g(lua9, "graphicsShadowQuality") == "5" and frame(lua9).result.text == "Put back 1 setting.", "after the fight it goes back")

# A /reload before the check ran keeps the old copy, and the reload checks instead.
lua10 = boot(db)
lua10.execute(SER + STUBS + 'SetCVar("graphicsSSAO", "2"); SetCVar("graphicsShadowQuality", "1")')
lua10.execute('FIRE("PLAYER_ENTERING_WORLD", true, false)')  # timers not run yet: the check is still waiting
db10 = logout(lua10)
lua11 = session(db10, 'SetCVar("graphicsSSAO", "2"); SetCVar("graphicsShadowQuality", "1")', login=False)
check(shown(lua11), "a /reload in the first seconds: the reload still warns")

# Another PC (a copied settings folder): a different graphics card, so nothing shows.
lua12 = session(db, 'SetCVar("graphicsSSAO", "2"); SetCVar("graphicsShadowQuality", "1");'
                ' C_VideoOptions.GetGxAdapterInfo = function() return { { name = "AMD Radeon RX 7900" } } end')
check(not shown(lua12), "a different graphics card: no window")

# Another WoW account logged out last in this game run (the copy is that account's, not this one's).
lua13 = session(db, 'SetCVar("graphicsSSAO", "2"); SetCVar("graphicsShadowQuality", "1");'
                ' C_CVar.RegisterCVar("eyeCandyWatch", ""); C_CVar.SetCVar("eyeCandyWatch", "someone-else")')
check(not shown(lua13), "another account logged out last: no window")

# A setting stored on the server (it follows the account or character): never counted.
lua14 = session(db, 'SetCVar("graphicsSSAO", "2"); SetCVar("graphicsShadowQuality", "1");'
                ' local info = C_CVar.GetCVarInfo; C_CVar.GetCVarInfo = function(n) local v, d = info(n);'
                ' return v, d, n == "graphicsShadowQuality", false end')
check(not shown(lua14), "a setting stored on the server: not counted")

# The city switch lowered settings at logout: the copy holds your own values, so leaving it is no change.
city = """
C_Map = { GetBestMapForUnit = function() return MAP end,
  GetMapInfo = function(id) return { mapID = id, mapType = 3, parentMapID = 13, flags = 0 } end }
MAP = 84; C_PvP = { GetZonePVPInfo = function() return nil end }
function IsInInstance() return false, "none" end
"""
lua15 = session(None, city + 'SetCVar("graphicsSSAO", "2")')
lua15.execute('SlashCmdList.EYECANDY("city on"); RUNTIMERS()')
check(g(lua15, "graphicsViewDistance") == "7", "in Stormwind the city switch lowered view distance")
db15 = logout(lua15)
check(ev(lua15, 'EyeCandyDB.patchWatch.snap.values.graphicsViewDistance') == "9", "the logout copy holds your own view distance, not the lowered one")
lua16 = session(db15, city + 'MAP = 37; SetCVar("graphicsSSAO", "2"); SetCVar("graphicsViewDistance", "7");'
                ' SetCVar("graphicsComputeEffects", "2"); SetCVar("entityLodDist", "10")')
check(g(lua16, "graphicsViewDistance") == "9", "logged in outside the city: the switch put view distance back")
check(not shown(lua16), "and nothing shows")
lua17 = session(db15, city + 'SetCVar("graphicsSSAO", "2"); SetCVar("graphicsViewDistance", "7");'
                ' SetCVar("graphicsComputeEffects", "2"); SetCVar("entityLodDist", "10")')
check(not shown(lua17), "logged in still in the city, settings still lowered: nothing shows")

# Autotune's test values at logout: the copy holds the settings from before it.
lua18 = session(None, 'SetCVar("graphicsSSAO", "2")')
lua18.execute('EyeCandyDB.autotune = { before = { graphicsShadowQuality = "5" } }; SetCVar("graphicsShadowQuality", "1")')
db18 = logout(lua18)
check(ev(lua18, 'EyeCandyDB.patchWatch.snap.values.graphicsShadowQuality') == "5", "Autotune left at logout: the copy holds the setting from before it")

# Compare showing "before" at logout: the copy holds "now".
lua19 = session(None, 'SetCVar("graphicsSSAO", "2")')
lua19.execute('EyeCandyDB.compare = { now = { graphicsShadowQuality = "5" }, label = "x" }; SetCVar("graphicsShadowQuality", "1")')
logout(lua19)
check(ev(lua19, 'EyeCandyDB.patchWatch.snap.values.graphicsShadowQuality') == "5", "Compare showing before at logout: the copy holds now")

# Long lists stay short.
many = ''.join('SetCVar("%s", "%s");' % (c, v) for c, v in (
    ("graphicsShadowQuality", "1"), ("graphicsLightMode", "0"), ("graphicsSSAO", "0"), ("graphicsDepthEffects", "0"),
    ("graphicsComputeEffects", "0"), ("graphicsLiquidDetail", "0"), ("graphicsPBRLiquidDetail", "0"),
    ("graphicsTextureResolution", "0"), ("graphicsViewDistance", "0"), ("graphicsEnvironmentDetail", "0")))
lua20 = session(db, many)
ls = lines(lua20)
check(len(ls) == 9 and ls[-1] == "And 2 more.", "ten changes: eight listed, then And 2 more. (%d lines, last %r)" % (len(ls), ls[-1] if ls else None))
check(all("—" not in l for l in ls + [frame(lua20).head.text]), "no em-dashes")

done()
