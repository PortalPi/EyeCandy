"""The instance switch (Situations.lua): /ec instance lowers your settings to Raid & PvP's in a dungeon,
raid, battleground or arena, and puts them back when you leave. It sits on the city switch.

Run alone: python tests/test_instance_switch.py
"""
from lib import boot, chat, check, done, addon

# The world: 37 Elwynn, 84 Stormwind. INSTANCE is what IsInInstance gives as its second value
# ("none", "party", "raid", "pvp", "arena", and the housing ones "neighborhood" and "interior").
# The game's own Raid and Battleground settings: RAIDsettingsEnabled and a raidGraphics twin for each
# graphics menu setting (Blizzard_Settings_Shared/Mainline/GraphicsOverrides.lua, forever branch).
STUBS = """
for k, v in pairs({ bloomUserMult = "1", cameraFov = "90", Contrast = "57", Brightness = "46", RAIDsettingsEnabled = "0" }) do C_CVar.RegisterCVar(k, v) end
for _, k in ipairs({ "ShadowQuality", "LiquidDetail", "PBRLiquidDetail", "ParticleDensity", "SSAO", "DepthEffects",
  "ComputeEffects", "OutlineMode", "TextureResolution", "SpellDensity", "ProjectedTextures", "LightMode",
  "ViewDistance", "EnvironmentDetail", "GroundClutter" }) do C_CVar.RegisterCVar("raidGraphics" .. k, "3") end
MAPS = {
  [13] = { mapType = 2, parentMapID = 947, flags = 0 },
  [84] = { mapType = 3, parentMapID = 13, flags = 0 },
  [37] = { mapType = 3, parentMapID = 13, flags = 0 },
}
MAP = 37; PVP = nil; INSTANCE = "none"
C_Map = {
  GetBestMapForUnit = function(unit) return MAP end,
  GetMapInfo = function(id) local m = MAPS[id]; if m then return { mapID = id, name = "map", mapType = m.mapType, parentMapID = m.parentMapID, flags = m.flags } end end,
}
C_PvP = { GetZonePVPInfo = function() return PVP end }
function IsInInstance() return INSTANCE ~= "none", INSTANCE end
"""


def start(svdb=None):
    lua = boot(svdb)
    lua.execute(STUBS)
    lua.execute('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}')
    return lua


def go(lua, kind, mapid=37):
    """Through a loading screen into an instance of this kind ("none" is the open world)."""
    lua.execute('INSTANCE = "%s"; MAP = %s; FIRE("PLAYER_ENTERING_WORLD", false, false); RUNTIMERS()' % (kind, mapid))


lua = start()
g = lambda n: lua.eval('GetCVar("%s")' % n)
ev = lambda s: lua.eval(s)
X = lua.execute

# Where am I? Only the four kinds count. Housing is an instance to the game, but not a fight.
for kind, want in (("party", "party"), ("raid", "raid"), ("pvp", "pvp"), ("arena", "arena"),
                   ("none", False), ("scenario", False), ("neighborhood", False), ("interior", False)):
    check(ev('(function() INSTANCE = "%s"; local r = NS.InstanceType(); INSTANCE = "none"; return r end)()' % kind) == want,
          "instance type %s counts as %r" % (kind, want))
check(ev('(function() local f = IsInInstance; IsInInstance = nil; local r = NS.InstanceType(); IsInInstance = f; return r end)()') == False,
      "no IsInInstance in this client: never in an instance")

# The caps are Raid & PvP's own values, and every one is a setting that costs more when higher.
caps = ev('NS.SITUATIONS[1].auto.caps')
raid = ev('NS.PresetValues("look:raid")')
check(ev('NS.SITUATIONS[1].key') == "raid" and ev('NS.SITUATIONS[1].auto.test') == "instance", "Raid & PvP has the instance switch")
check(all(str(raid[k]) == str(v) or float(raid[k]) == float(v) for k, v in caps.items()), "each cap is Raid & PvP's own value")
check(not any(k in caps for k in ("cameraFov", "cameraDistanceMaxZoomFactor", "vrsValar", "lodObjectCullSize", "RenderScale")),
      "no cap on a setting that is cheaper higher, or not a cost (field of view, zoom, shading rate, cull size, render scale)")

# Off until you turn it on.
check(not ev('NS.IsAutoSituationOn("raid")'), "the instance switch is off by default")
go(lua, "party")
check(g("graphicsShadowQuality") == "5", "switch off: a dungeon changes nothing")
go(lua, "none")

# Turn it on outside: nothing changes yet.
X('SlashCmdList.EYECANDY("instance")')
out = chat(lua)
check(ev('NS.IsAutoSituationOn("raid")') == True and any("puts them back when you leave" in l for l in out), "/ec instance turns it on and says what it does")
check(g("graphicsShadowQuality") == "5", "turned on in Elwynn: nothing changes yet")

# Into a dungeon: down to Raid & PvP's, only where yours are higher. No backup.
X('SetCVar("graphicsSSAO", "2"); CHAT = {}')
before = len(ev('NS.ListBackups()'))
go(lua, "party")
check(g("graphicsShadowQuality") == "4" and g("graphicsLightMode") == "2" and g("graphicsViewDistance") == "8", "in a dungeon: shadows 4, lighting 2, view distance 8")
check(g("graphicsParticleDensity") == "1" and g("graphicsDepthEffects") == "0" and g("weatherDensity") == "0" and g("bloomUserMult") == "0.4",
      "particles 1, depth effects off, no weather, less glow")
check(g("graphicsSSAO") == "2", "a setting already lower than Raid & PvP's is not raised")
check(g("cameraFov") == "90" and g("cameraDistanceMaxZoomFactor") == "1.9", "field of view and zoom are left alone")
out = chat(lua)
check(any("In a dungeon: lowered " in l and "Raid & PvP" in l and "back when you leave" in l for l in out), "chat says where, how many and that they go back (%r)" % out)
check(len(ev('NS.ListBackups()')) == before, "no backup is taken")
check(ev('NS.ActiveSituationName()') == "Raid & PvP" and ev('NS.ActiveSituationKey()') == "raid", "it knows it is in Raid & PvP")
check(ev('NS.SituationNote()') == "In a dungeon: some settings lowered", "the card's line names the place")
check(ev('NS.SituationValue("graphicsShadowQuality", "4")') == "5", "backups get your own shadows, not the lowered 4")

# Out again: each goes back.
X('CHAT = {}')
go(lua, "none")
check(g("graphicsShadowQuality") == "5" and g("graphicsLightMode") == "3" and g("graphicsViewDistance") == "9" and g("graphicsSSAO") == "2"
      and g("bloomUserMult") == "1" and g("weatherDensity") == "2", "leaving puts each setting back")
check(any("Left the dungeon: put back " in l for l in chat(lua)), "chat says it left the dungeon and put them back")
check(ev('NS.ActiveSituationName()') is None and ev('NS.SituationNote()') is None, "and it is out of Raid & PvP")

# A setting you change inside stays as you set it.
go(lua, "raid")
X('SetCVar("graphicsViewDistance", "6"); CHAT = {}')
go(lua, "none")
check(g("graphicsViewDistance") == "6" and g("graphicsShadowQuality") == "5", "your own change in the raid stays; the rest go back")
check(any("Left 1 alone that changed while you were there" in l for l in chat(lua)), "chat says how many were left alone")
X('SetCVar("graphicsViewDistance", "9")')

# Arenas and battlegrounds count too.
for kind, word in (("pvp", "battleground"), ("arena", "arena")):
    go(lua, kind)
    check(g("graphicsShadowQuality") == "4" and ev('NS.SituationNote()') == "In %s %s: some settings lowered" % ("an" if word == "arena" else "a", word), "in a %s it switches" % word)
    go(lua, "none")
check(g("graphicsShadowQuality") == "5", "and puts back after each")

# Housing is not a fight: nothing changes.
go(lua, "neighborhood")
check(g("graphicsShadowQuality") == "5" and ev('NS.ActiveSituationName()') is None, "in a neighbourhood nothing changes")
go(lua, "none")

# Straight from a dungeon into a raid (a queue that pops inside): the place is new, so it starts again.
go(lua, "party")
go(lua, "raid")
check(ev('NS.SituationNote()') == "In a raid: some settings lowered" and g("graphicsShadowQuality") == "4", "dungeon to raid: now in a raid, still lowered")
go(lua, "none")
check(g("graphicsShadowQuality") == "5", "and out puts back your own")

# The game's own Raid and Battleground settings: in a raid or battleground the game uses those for its
# graphics menu settings, so Eye Candy leaves those alone and lowers only the rest. A dungeon and an arena
# are not covered by the game's raid settings, so there it works as before.
X('SetCVar("RAIDsettingsEnabled", "1"); CHAT = {}')
for kind in ("raid", "pvp"):
    go(lua, kind)
    check(g("graphicsShadowQuality") == "5" and g("graphicsViewDistance") == "9" and g("graphicsParticleDensity") == "4",
          "game's raid settings on, in %s: the game's own graphics settings are left to the game" % kind)
    check(g("weatherDensity") == "0" and g("bloomUserMult") == "0.4", "and the rest (weather, glow) still come down in %s" % kind)
    out = chat(lua)
    check(any("The game's own Raid and Battleground settings look after the rest." in l for l in out), "chat says the game looks after the rest (%r)" % out)
    go(lua, "none")
    check(g("weatherDensity") == "2" and g("bloomUserMult") == "1", "leaving puts weather and glow back")
    X('CHAT = {}')
go(lua, "party")
check(g("graphicsShadowQuality") == "4", "game's raid settings on, in a dungeon: Eye Candy lowers shadows as before")
go(lua, "none")
X('SetCVar("RAIDsettingsEnabled", "0")')

# An instance is never a city: the city switch stays out, and the two hand over cleanly.
X('NS.SetAutoSituation("city", true)')
go(lua, "party", 84)
check(ev('NS.ActiveSituationKey()') == "raid", "both on, a dungeon whose map is Stormwind's: the instance switch, not the city")
X('CHAT = {}')
go(lua, "none", 84)
check(ev('NS.ActiveSituationKey()') == "city" and g("graphicsShadowQuality") == "5" and g("graphicsViewDistance") == "7",
      "out of the dungeon into Stormwind: your settings back, then the city lowers its own")
go(lua, "raid")
check(ev('NS.ActiveSituationKey()') == "raid" and g("graphicsViewDistance") == "8", "city to raid: the city puts back, the raid lowers")
go(lua, "none")
check(g("graphicsViewDistance") == "9" and g("graphicsShadowQuality") == "5", "out to Elwynn: all yours again")
X('NS.SetAutoSituation("city", false)')

# Out of an instance with the map not known yet: you are out, so the switch ends at once.
go(lua, "party")
X('INSTANCE = "none"; MAP = nil; NS.SetAutoSituation("city", true); FIRE("PLAYER_ENTERING_WORLD", false, false); RUNTIMERS()')
check(g("graphicsShadowQuality") == "5" and ev('NS.ActiveSituationName()') is None, "the city can't tell yet, but you are out of the dungeon: put back")
X('MAP = 37; RUNTIMERS(); NS.SetAutoSituation("city", false)')

# Never in combat: it waits for the fight to end, and the box says so.
X('INCOMBAT = true')
go(lua, "raid")
check(g("graphicsShadowQuality") == "5", "in combat at the door: nothing changes")
check(ev('NS.SituationWaiting()') == True, "it knows it is waiting")
X('SlashCmdList.EYECANDY("")')
check("Waits for the fight to end" in ev('EyeCandyMainFrame.pages.presets.instanceBox.text.text'), "the box says it waits for the fight")
X('INCOMBAT = false; FIRE("PLAYER_REGEN_ENABLED")')
check(g("graphicsShadowQuality") == "4" and not ev('NS.SituationWaiting()'), "after the fight it switches")
# A zone change in a fight with nothing to switch: it is not waiting for anything.
X('INCOMBAT = true; FIRE("ZONE_CHANGED_INDOORS"); RUNTIMERS(); NS.RefreshUI()')
check(not ev('NS.SituationWaiting()') and "Waits" not in ev('EyeCandyMainFrame.pages.presets.instanceBox.text.text'),
      "a zone change mid-fight in the same raid: no waiting line")
X('INCOMBAT = false')
go(lua, "none")

# Yours already at or under Raid & PvP's: it is on, but says nothing was lowered.
X('LOW = {}; for k, v in pairs(NS.SITUATIONS[1].auto.caps) do LOW[k] = GetCVar(k); SetCVar(k, v) end; CHAT = {}')
go(lua, "party")
check(ev('NS.ActiveSituationKey()') == "raid" and chat(lua) == [], "nothing to lower: on, and chat says nothing")
check(ev('NS.SituationNote()') is False and ev('NS.RunningNote()') is None, "the card and title claim nothing")
X('NS.RefreshUI()')
check("Nothing needed lowering" in ev('EyeCandyMainFrame.pages.presets.instanceBox.text.text'), "the box says nothing needed lowering")
go(lua, "none")
X('for k, v in pairs(LOW) do SetCVar(k, v) end')

# Steps aside while Autotune runs, and switches once it is done.
X('REAL_RUN = NS.Autotune.IsRunning; NS.Autotune.IsRunning = function() return true end')
go(lua, "party")
check(g("graphicsShadowQuality") == "5", "Autotune running: the switch waits")
X('NS.Autotune.IsRunning = REAL_RUN; RUNTIMERS()')
check(g("graphicsShadowQuality") == "4", "Autotune done: it switches")
go(lua, "none")

# A Compare showing "before" ends first.
X('NS.ApplyPresetById("look:beautiful")')
own = g("graphicsShadowQuality")
check(ev('NS.ToggleCompare()') is True, "set-up: Compare shows before")
go(lua, "party")
check(not ev('NS.IsComparing()'), "going into a dungeon ends Compare")
go(lua, "none")
check(g("graphicsShadowQuality") == own, "and out again gives your own shadows")

# Eye Candy's own apply inside is lowered again where it raised something.
go(lua, "raid")
X('NS.ApplyAll(false, true)')
check(g("graphicsShadowQuality") == "4" and g("graphicsViewDistance") == "8", "pressing Apply in a raid: lowered again")
go(lua, "none")

# Turned off inside: it puts things back at once.
go(lua, "party")
X('CHAT = {}; SlashCmdList.EYECANDY("instance off")')
check(g("graphicsShadowQuality") == own and not ev('NS.IsAutoSituationOn("raid")'), "/ec instance off in a dungeon puts things back")
check(any("no longer changes settings in dungeons" in l for l in chat(lua)), "and says so")
go(lua, "none")

# Help lists it.
X('SlashCmdList.EYECANDY("help")')
out = chat(lua)
check(any("/ec instance  lower" in l for l in out) and any("/ec city" in l for l in out), "help lists /ec instance and /ec city")
check(any("the Raid & PvP preset's settings" in l for l in out) and not any("PvP's in" in l for l in out),
      "the help says \"the Raid & PvP preset's settings\", not \"Raid & PvP's\"")

# The Presets tab: a tick box under Raid & PvP, with its line on the screen.
X('NS.RefreshUI()')
P ='EyeCandyMainFrame.pages.presets'
box = P + '.instanceBox'
check(ev(box + '.shown') == True and ev(box + '.text.text') == "Switch in dungeons, raids, battlegrounds and arenas by itself", "a tick box sits under Raid & PvP, its label naming arenas too (%r)" % ev(box + '.text.text'))
check(ev(box + '.note.shown') == True and "dungeons, raids, battlegrounds and arenas" in ev(box + '.note.text') and "go back when you leave" in ev(box + '.note.text'),
      "a grey line under it says what it does (%r)" % ev(box + '.note.text'))
check(len(ev(box + '.note.text')) <= 115, "the line is no longer than the city one plus a little (%d)" % len(ev(box + '.note.text')))
X('TIP = {}; GameTooltip.AddLine = function(self, t) TIP[#TIP + 1] = t end; %s.scripts.OnEnter(%s); GameTooltip.AddLine = nil' % (box, box))
check("Never in combat" in ev('TIP[2]') and "Raid and Battleground settings" in ev('TIP[2]'), "its tooltip says when, and how it works with the game's own raid settings")
check("PvP's." not in ev('TIP[2]') and "PvP's." not in ev(box + '.note.text'), "neither the tooltip nor the line says \"Raid & PvP's.\"")
X('%s.scripts.OnClick(%s)' % (box, box))
check(ev('NS.IsAutoSituationOn("raid")') == True, "ticking the box turns it on")
go(lua, "raid")
check("On now: in a raid" in ev(box + '.text.text'), "inside, the box says it is on now")
check("On now" not in ev(P + '.cityBox.text.text'), "and the city box does not")
check(ev(P + '.card.note.text') == "|cffffd100In a raid: some settings lowered|r", "the card says so too (%r)" % ev(P + '.card.note.text'))
go(lua, "none")

# A logout inside: the next login outside puts your settings back.
sv = ('EyeCandyDB = { tiers = {}, extras = {}, advanced = {}, keepApplied = false, autoSituations = { raid = true },'
      ' situationActive = { key = "raid", place = "party", set = { graphicsShadowQuality = { was = "5", now = "4" } } } }')
lua = boot(sv)
lua.execute(STUBS)
lua.execute('SetCVar("graphicsShadowQuality", "4"); FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS()')
check(lua.eval('GetCVar("graphicsShadowQuality")') == "5" and lua.eval('NS.ActiveSituationName()') is None, "logged out in a dungeon, logged in outside: shadows back to 5")

# The README lists the command.
readme = open(addon + '../README.md', encoding='utf-8').read()
check("`/ec instance`" in readme, "the README's command table has /ec instance")

done()
