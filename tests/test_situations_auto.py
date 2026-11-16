"""The city switch (Situations.lua): /ec city lowers the crowd costs in a capital city on top of
your own settings, and puts them back when you leave.

Run alone: python tests/test_situations_auto.py
"""
from lib import boot, chat, check, done

# Dials the Looks set that the stub client doesn't register by itself, and a small world of maps.
# 84 Stormwind (a known id), 37 Elwynn, 60 an inn in Goldshire, 2000 a city the game flags but Eye Candy
# has no id for, 2001 a building inside it, 13 the continent.
STUBS = """
for k, v in pairs({ bloomUserMult = "1", cameraFov = "90", Contrast = "57", Brightness = "46" }) do C_CVar.RegisterCVar(k, v) end
MAPS = {
  [13] = { mapType = 2, parentMapID = 947, flags = 0 },
  [84] = { mapType = 3, parentMapID = 13, flags = 0 },
  [37] = { mapType = 3, parentMapID = 13, flags = 0 },
  [60] = { mapType = 5, parentMapID = 37, flags = 0 },
  [2000] = { mapType = 3, parentMapID = 13, flags = 1048576 + 4 },
  [2001] = { mapType = 5, parentMapID = 2000, flags = 0 },
}
MAP = 37; PVP = nil; INSTANCE = false
C_Map = {
  GetBestMapForUnit = function(unit) return MAP end,
  GetMapInfo = function(id) local m = MAPS[id]; if m then return { mapID = id, name = "map", mapType = m.mapType, parentMapID = m.parentMapID, flags = m.flags } end end,
}
C_PvP = { GetZonePVPInfo = function() return PVP end }
function IsInInstance() return INSTANCE, INSTANCE and "party" or "none" end
"""


def start(svdb=None):
    lua = boot(svdb)
    lua.execute(STUBS)
    lua.execute('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}')
    return lua


def walk(lua, mapid):
    lua.execute('MAP = %s; FIRE("ZONE_CHANGED_NEW_AREA"); FIRE("ZONE_CHANGED"); RUNTIMERS()' % mapid)


lua = start()
g = lambda n: lua.eval('GetCVar("%s")' % n)
ev = lambda s: lua.eval(s)
backups = lambda: len(ev('NS.ListBackups()'))

# Where am I?
for mapid, want, why in ((84, True, "Stormwind by its map id"), (37, False, "Elwynn Forest"),
                         (60, False, "an inn outside a city"), (2000, True, "a city the game flags"),
                         (2001, True, "a building inside a flagged city")):
    check(ev('(function() MAP = %d; return NS.InCapitalCity() end)()' % mapid) == want, "in a city: %s is %s" % (why, want))
check(ev('(function() MAP = nil; return NS.InCapitalCity() end)()') is None, "no map yet (after a loading screen): not sure")
check(ev('(function() MAP = 37; PVP = "sanctuary"; local r = NS.InCapitalCity(); PVP = nil; return r end)()') == True, "a sanctuary counts as a city")
check(ev('(function() MAP = 84; INSTANCE = true; local r = NS.InCapitalCity(); INSTANCE = false; return r end)()') == False, "inside a dungeon is never a city")
lua.execute('MAP = 37')

# Off until you turn it on.
check(not ev('NS.IsAutoSituationOn("city")'), "the city switch is off by default")
walk(lua, 84)
check(g("graphicsViewDistance") == "9", "switch off: walking into Stormwind changes nothing")
walk(lua, 37)

# Turn it on outside a city: nothing changes yet.
lua.execute('SlashCmdList.EYECANDY("city")')
out = chat(lua)
check(ev('NS.IsAutoSituationOn("city")') == True and any("until you leave" in l for l in out), "/ec city turns it on and says what it does")
check(g("graphicsViewDistance") == "9", "turned on in Elwynn: nothing changes yet")

# Walk into Stormwind: the four crowd costs come down, only where yours are higher. No backup.
lua.execute('SetCVar("entityLodDist", "20"); SetCVar("graphicsEnvironmentDetail", "5")')
before = backups()
walk(lua, 84)
check(g("graphicsViewDistance") == "7" and g("graphicsComputeEffects") == "2" and g("entityLodDist") == "10", "in Stormwind: view distance 7, compute effects 2, far characters 10")
check(g("graphicsEnvironmentDetail") == "5", "a setting already lower than the cap is not raised")
check(g("graphicsShadowQuality") == "5" and g("graphicsSSAO") == "4", "shadows and SSAO are left alone")
check(any("lowered 3 settings" in l for l in chat(lua)), "chat says how many came down")
check(backups() == before, "no backup is taken")
check(ev('NS.ActiveSituationName()') == "Capital city", "it knows it is in the Capital city Situation")
check(ev('NS.SituationValue("graphicsViewDistance", "7")') == "9" and ev('NS.SituationValue("graphicsEnvironmentDetail", "5")') == "5", "backups get your own value for a lowered setting, and the rest as they are")
check(ev('NS.SituationValue("graphicsViewDistance", "8")') == "8", "a value that isn't the lowered one is yours")

# A building inside the city, and a loading screen with no map yet: still in.
walk(lua, 2001)
lua.execute('MAP = nil; FIRE("PLAYER_ENTERING_WORLD", false, false); RUNTIMERS()')
check(g("graphicsViewDistance") == "7" and ev('NS.ActiveSituationName()') == "Capital city", "no map after a loading screen: it stays put")
lua.execute('MAP = 84; RUNTIMERS()')
check(ev('NS.ActiveSituationName()') == "Capital city", "and asks again once the map is known")

# Leave: each goes back.
walk(lua, 37)
check(g("graphicsViewDistance") == "9" and g("graphicsComputeEffects") == "4" and g("entityLodDist") == "20" and g("graphicsEnvironmentDetail") == "5", "leaving puts each setting back")
check(any("put back 3 settings" in l for l in chat(lua)), "chat says how many went back")
check(ev('NS.ActiveSituationName()') is None, "and it is out of the Situation")

# A setting you change yourself in the city is left alone when you leave.
walk(lua, 84)
lua.execute('SetCVar("graphicsViewDistance", "8"); CHAT = {}')
walk(lua, 37)
out = chat(lua)
check(g("graphicsViewDistance") == "8" and g("graphicsComputeEffects") == "4", "your own change in the city stays; the rest go back")
check(any("1 setting changed while you were there, so it stays" in l for l in out), "chat says how many were left alone")
lua.execute('SetCVar("graphicsViewDistance", "9")')

# A login with no map yet, then the map arrives: the retry switches.
lua.execute('MAP = nil; FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS()')
check(g("graphicsViewDistance") == "9", "logging in, map not known yet: nothing changes")
lua.execute('MAP = 84; RUNTIMERS()')
check(g("graphicsViewDistance") == "7", "the retry finds Stormwind and switches")
walk(lua, 37)

# Never in combat: the switch waits for the fight to end.
lua.execute('INCOMBAT = true')
walk(lua, 84)
check(g("graphicsViewDistance") == "9", "in combat at the gate: nothing changes")
lua.execute('INCOMBAT = false; FIRE("PLAYER_REGEN_ENABLED")')
check(g("graphicsViewDistance") == "7", "after the fight it switches")
walk(lua, 37)

# Eye Candy's own re-apply in a city is lowered again where it raised something; a change of yours is not.
lua.execute('NS.ApplyPresetById("look:beautiful")')
check(ev('NS.BackSteps()[1].name') == "Beautiful", "set-up: Beautiful applied outside, today's newest step")
walk(lua, 84)
check(g("entityLodDist") == "10" and g("graphicsViewDistance") == "7", "Beautiful in Stormwind: lowered")
lua.execute('NS.ApplyAll(true, true)')
check(g("entityLodDist") == "10", "the quiet re-apply after Options puts far characters back to 20; it is lowered again")
lua.execute('NS.ApplyAll(false, true)')
check(g("graphicsViewDistance") == "7" and g("graphicsComputeEffects") == "2", "pressing Apply in the city raises view distance and compute effects; both are lowered again")
check(ev('NS.ApplyPresetById("look:crisp")') == True and g("graphicsComputeEffects") == "2" and g("entityLodDist") == "10", "a preset picked in the city is lowered too")
lua.execute('SetCVar("graphicsViewDistance", "9"); NS.ApplyAll(false, true)')
check(g("graphicsViewDistance") == "9", "view distance you raised yourself stays yours through an Apply")
# An apply that fails part-way still gets lowered, and the error still shows.
lua.execute('ORIG_CAT = NS.ApplyCategory; NS.ApplyCategory = function() SetCVar("graphicsComputeEffects", "4"); error("boom") end')
check(ev('(function() local ok = pcall(NS.ApplyAll, false, true); return ok end)()') == False, "a failing apply still raises its error")
lua.execute('NS.ApplyCategory = ORIG_CAT')
check(g("graphicsComputeEffects") == "2", "and what it raised before failing is lowered again")
walk(lua, 37)
check(g("graphicsComputeEffects") == "4" and g("entityLodDist") == "20", "leaving puts back the preset's own values")
check(g("graphicsViewDistance") == "9", "and your own view distance stays")

# Backups, saved presets and Back record your own values in a city, not the lowered ones, and a restore
# there (Back included) is lowered again.
lua.execute('NS.ApplyPresetById("look:beautiful")')
own = g("graphicsViewDistance")
walk(lua, 84)
check(g("graphicsViewDistance") == "7" and own != "7", "set-up: Beautiful outside, then Stormwind lowers view distance to 7")
check(ev('NS.BackSteps()[1].name') == "Beautiful", "walking into a city is no change of your own: Beautiful is still the newest step")
check(ev('NS.CreateBackup("manual", "In town").values.graphicsViewDistance') == own, "a backup made in the city holds your own view distance, not the lowered 7")
check(ev('NS.CountBackupChanges(NS.ListBackups()[1].id)') == 0, "and it counts no change against now")
check(ev('NS.SaveCurrentAsPreset("Town").values.graphicsViewDistance') == own, "a preset saved in the city holds your own view distance")
lua.execute('SetCVar("graphicsViewDistance", "5"); NS.RestoreBackupById(NS.ListBackups()[1].id)')
check(g("graphicsViewDistance") == "7", "restoring it in the city puts your view distance back, and the city lowers it again")
walk(lua, 37)
check(g("graphicsViewDistance") == own, "leaving puts your own view distance back")
lua.execute('SetCVar("graphicsViewDistance", "8"); NS.ApplyPresetById("look:crisp")')
walk(lua, 84)
check(ev('NS.BackSteps()[1].name') == "Crisp", "set-up: a preset outside, then Stormwind: Crisp is the newest step")
lua.execute('SlashCmdList.EYECANDY("back")')
check(g("graphicsViewDistance") == "7" and ev('NS.BackSteps()[1].name') != "Crisp", "Back in the city goes back, and the city keeps view distance lowered")
walk(lua, 37)
check(g("graphicsViewDistance") == "8", "leaving after Back gives the view distance from before the preset")
lua.execute('SetCVar("graphicsViewDistance", "9")')

# Review round. Your own preset applied in a city is lowered too, and its hidden values are kept as yours.
lua.execute('NS.ApplyPresetById("look:beautiful")')
own_lod = g("entityLodDist")
town = ev('NS.SaveCurrentAsPreset("Town 2")')
walk(lua, 84)
check(ev('NS.ApplyPresetById("%s")' % town['id']) == True and g("graphicsViewDistance") == "7" and g("entityLodDist") == "10", "your own preset applied in the city is lowered too")
check(ev('EyeCandyDB.advanced.entityLodDist') == float(own_lod), "and keeps your far-character value, not the lowered 10")
walk(lua, 37)
check(g("entityLodDist") == own_lod, "leaving puts it back")
# Leaving while Compare shows "before": Compare ends first, so nothing is stuck low.
lua.execute('SetCVar("graphicsViewDistance", "8"); NS.ApplyPresetById("look:beautiful")')
own = g("graphicsViewDistance")
walk(lua, 84)
check(ev('NS.ToggleCompare()') is True and g("graphicsViewDistance") == "8", "set-up: in the city, Compare shows before (view distance 8)")
walk(lua, 37)
check(not ev('NS.IsComparing()') and g("graphicsViewDistance") == own, "leaving the city ends Compare and puts your own view distance back")
lua.execute('SetCVar("graphicsViewDistance", "9")')

# Turned off in a city: it puts things back at once.
walk(lua, 84)
lua.execute('CHAT = {}; SlashCmdList.EYECANDY("city off")')
check(g("graphicsViewDistance") == "9" and not ev('NS.IsAutoSituationOn("city")'), "/ec city off in a city puts things back")
check(any("no longer changes settings" in l for l in chat(lua)), "and says so")

# Help lists it, and the rest of the slash commands still work.
lua.execute('SlashCmdList.EYECANDY("help")')
out = chat(lua)
check(any("/ec city" in l for l in out) and any("/ec report" in l for l in out), "help lists /ec city after Eye Candy's own lines")

# A logout in a city: the next login outside one puts your settings back.
sv = ('EyeCandyDB = { tiers = {}, extras = {}, advanced = {}, keepApplied = false, autoSituations = { city = true },'
      ' situationActive = { key = "city", set = { graphicsViewDistance = { was = "9", now = "7" } } } }')
lua = boot(sv)
lua.execute(STUBS)
lua.execute('SetCVar("graphicsViewDistance", "7"); FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS()')
check(lua.eval('GetCVar("graphicsViewDistance")') == "9" and lua.eval('NS.ActiveSituationName()') is None, "logged out in a city, logged in outside: view distance back to 9")

done()
