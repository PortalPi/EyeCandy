"""Checks for the tooltip fixes (roadmap step 6): every dial, Extra and Standard tooltip puts
Blizzard's words first (or "Not documented by Blizzard"), then one plain line, then the game
default; and the eight fixes from the PLAN audit.
Run: python tests/test_tooltips.py"""
from lib import boot, check, done

# Blizzard's help text for a few CVars (as ConsoleGetAllCommands gives it, from docs/cvar_audit.txt),
# and the menu's own tooltip for Depth Effects. Loaded before the addon.
HELP = """
local help = {
  DepthBasedOpacity = "Enable/Disable Soft Edge Effect", particleMTDensity = "Multi-Tex particle density",
  ResampleSharpness = "FSR sharpness strength [0.0-2.0]. 0 is full strength. -1 to disable.",
  SkyCloudLOD = "Texture resolution for clouds", specular = "Specular lighting multiplier (0-1)",
  terrainMipLevel = "Terrain blend map mip level", graphicsDepthEffects = "UI value of the graphics setting",
}
for k, v in pairs({ RenderScale = "1", ResampleQuality = "3", ResampleSharpness = "0.2", DepthBasedOpacity = "1",
  particleMTDensity = "100", SkyCloudLOD = "0", specular = "1", terrainMipLevel = "0", graphicsDepthEffects = "2" }) do
  C_CVar.RegisterCVar(k, v)
end
local all = ConsoleGetAllCommands
function ConsoleGetAllCommands()
  local t = all()
  for _, c in ipairs(t) do c.help = help[c.command] end
  return t
end
OPTION_TOOLTIP_DEPTH_EFFECTS = "Controls the rendering of depth-based particle effects.  Decreasing this may improve performance."
"""

SETUP = """
local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
mt.__index = function(t, k) if k == "GetText" then return function(self) return self.text end end return index(t, k) end
function LINES(text) local t = {} for l in (text .. "\\n"):gmatch("(.-)\\n") do t[#t + 1] = l end return t end
-- nil when the tooltip has the shape: Blizzard's words, the plain line, the game default.
function SHAPE(text, plain, wantDefault)
  local l = LINES(text)
  if not (l[1]:find('^Blizzard: "') or l[1]:find("Not documented by Blizzard")) then return "first line is " .. l[1] end
  local i = 2
  if plain ~= false then
    if plain and l[2] ~= plain then return "second line is " .. tostring(l[2]) end
    if not plain and (l[2] == nil or l[2] == "" or l[2]:find("^Game default")) then return "no plain line" end
    i = 3
  end
  if wantDefault and not (l[i] or ""):find("^Game default: ") then return "line " .. i .. " is " .. tostring(l[i]) end
end
function DIAL(cvar) for _, g in ipairs(NS.ADVANCED) do for _, d in ipairs(g.rows) do if d[1] == cvar then return d end end end end
function STDROW(cvar) for _, r in ipairs(NS.stdRows) do if r.def.cvar == cvar then return r end end end
function EXROW(key) for _, r in ipairs(NS.extraRows) do if r.ex.key == key then return r end end end
"""

lua = boot(svdb=HELP)
lua.execute(SETUP)
E = lambda e: lua.eval(e)
lua.execute('FIRE("PLAYER_LOGIN"); SlashCmdList.EYECANDY(""); NS.ShowTab("hidden")')

# The rule, on every tooltip
bad = E("""(function()
  local bad = {}
  for _, g in ipairs(NS.ADVANCED) do for _, d in ipairs(g.rows) do
    local _, def = NS.GetInfo(d[1])
    local why = SHAPE(NS.DialTooltip(d), d.note or false, def ~= nil)
    if why then bad[#bad + 1] = d[1] .. ": " .. why end
  end end
  return table.concat(bad, "; ")
end)()""")
check(bad == "", "every dial tooltip: Blizzard's words, the plain line, the game default (%s)" % bad)
bad = E("""(function()
  local bad = {}
  for _, ex in ipairs(NS.EXTRAS) do
    local _, def = NS.GetInfo(ex.cvar)
    local why = SHAPE(NS.ExtraTooltip(ex), ex.desc:match("^[^\\n]*"), def ~= nil)
    if why then bad[#bad + 1] = ex.key .. ": " .. why end
  end
  return table.concat(bad, "; ")
end)()""")
check(bad == "", "every Extra tooltip: Blizzard's words, the first line of its text, the game default (%s)" % bad)
bad = E("""(function()
  local bad = {}
  for _, g in ipairs(NS.STANDARD) do for _, row in ipairs(g.rows) do
    local def = row.cvar and select(2, NS.GetInfo(row.cvar))
    local why = SHAPE(NS.StandardTooltip(row), nil, row.kind ~= "info" and def ~= nil)
    if not why and row.kind ~= "info" and not row.master and not row.plain then why = "no plain line written" end
    if why then bad[#bad + 1] = (row.cvar or row.key) .. ": " .. why end
  end end
  return table.concat(bad, "; ")
end)()""")
check(bad == "", "every Standard tooltip: Blizzard's words, a plain line, the game default (%s)" % bad)
check(E('LINES(NS.DialTooltip(DIAL("SkyCloudLOD")))[1]') == 'Blizzard: "Texture resolution for clouds"', "a dial quotes Blizzard's help text")
check(E('LINES(NS.ExtraTooltip(NS.EXTRAS[3]))[1]') == 'Blizzard: "FSR sharpness strength [0.0-2.0]. 0 is full strength. -1 to disable."', "the sharpness Extra quotes Blizzard, -1 included")
check("Not documented by Blizzard" in E('LINES(NS.DialTooltip(DIAL("componentEmissive")))[1]'), "a CVar with no help text says Not documented by Blizzard")

# 1. Depth effects are soft particles, not depth of field
d = 'DIAL("graphicsDepthEffects")'
check("soft particles" in E(d + '[2]') and "not depth of field" in E(d + '.note').lower(), "the depth effects dial is soft particles, and says it isn't depth of field")
check(E('LINES(NS.DialTooltip(%s))[1]' % d).startswith('Blizzard: "Controls the rendering of depth-based particle effects.'), "it quotes the menu's own tooltip, not 'UI value of the graphics setting'")
lua.execute('OPTION_TOOLTIP_DEPTH_EFFECTS = nil')
check(E('LINES(NS.DialTooltip(%s))[1]' % d).startswith('Blizzard: "Controls the rendering of depth-based particle effects.'), "without the game's string it still quotes the menu's words (the Standard tab's copy), not the junk help text")
looks = E("""(function()
  local bad = {}
  for _, list in ipairs({ NS.LOOKS, NS.SITUATIONS or {} }) do for _, l in ipairs(list) do
    if l.desc:lower():find("depth of field") or l.desc:lower():find("depth%-of%-field") then bad[#bad + 1] = l.name end
  end end
  return table.concat(bad, ", ")
end)()""")
check(looks == "", "no Look promises depth of field (%s)" % looks)
check("soft particles" in E('NS.LookTooltip(NS.LOOKS[1])'), "a Look's tooltip calls the setting soft particles")
check(E('(function() for _, c in ipairs(NS.CATEGORIES) do for _, r in ipairs(c.cvars) do if r[1] == "graphicsDepthEffects" then return r[2] end end end end)()') == "Depth effects (soft particles)", "the Lighting tier names it soft particles too")

# 2. Resample Quality is ignored above 100% render scale
lua.execute('SetCVar("RenderScale", "1.5"); NS.ShowTab("standard"); NS.RefreshUI()')
check(E('STDROW("ResampleQuality").ignored') == True and "ignored" in E('STDROW("ResampleQuality").valueText.text'), "Standard: Resample Quality shows as ignored at 150% render scale")
check("Ignored now" in E('NS.StandardTooltip(STDROW("ResampleQuality").def)'), "and its tooltip says why")
lua.execute('SetCVar("RenderScale", "0.8"); NS.RefreshUI()')
check(E('STDROW("ResampleQuality").ignored') == False, "at 80% it is live again")
check("Ignored now" not in E('NS.StandardTooltip(STDROW("ResampleQuality").def)'), "and its tooltip no longer says it is ignored")
lua.execute('NS.ShowTab("hidden"); EyeCandyDB.extras.renderScale = 1.5; NS.RefreshUI()')
check(E('EXROW("resample").ignored') == True and "ignored" in E('EXROW("resample").status.text'), "Hidden: the resample filter Extra shows as ignored when the render scale Extra is 150%")
check("Ignored now" in E('NS.ExtraTooltip(EXROW("resample").ex)'), "and its tooltip says why")
lua.execute('EyeCandyDB.extras.renderScale = 0.75; NS.RefreshUI()')
check(E('EXROW("resample").ignored') == False, "with the render scale Extra at 75% it is live")
lua.execute("""EyeCandyDB.extras.renderScale = nil; SetCVar("RenderScale", "1")
for _, c in ipairs(NS.CATEGORIES) do for _, r in ipairs(c.cvars) do if r[1] == "RenderScale" then CLARITY = c.key; EyeCandyDB.tiers[c.key] = 5 end end end
NS.RefreshUI()""")
check(E('(NS.TierValueFor("RenderScale"))') == 1.5 and E('EXROW("resample").ignored') == True, "with the Extra on Use tier, a 150% tier counts: Apply will set 150%, so the filter is ignored")
lua.execute('EyeCandyDB.tiers[CLARITY] = 1; NS.RefreshUI()')
check(E('EXROW("resample").ignored') == False, "and a 90% tier counts the other way")

# 3 to 8: sharpness Off (done in step 5, see test_sliders.py) and the relabels
check(E('DIAL("particleMTDensity")[2]') == "Multi-texture particle density %", "particleMTDensity is Multi-texture, not multithreaded")
sp = 'DIAL("specular")'
check(E(sp + '.kind') is None and E(sp + '[3]') == 0 and E(sp + '[4]') == 1 and E(sp + '[5]') == 0.05, "specular is a 0 to 1 slider, not a toggle")
check(E('(function() for _, r in ipairs(NS.advRows) do if r.d[1] == "specular" then return r.slider ~= nil end end end)()') == True, "and the Hidden tab shows it as a slider")
check(E('DIAL("DepthBasedOpacity")[2]') == "Soft edges on effects" and "robably" not in E('DIAL("DepthBasedOpacity").note'), "DepthBasedOpacity is Soft edges on effects, with the guess dropped")
check(E('DIAL("SkyCloudLOD")[2]') == "Cloud texture resolution" and "unconfirmed" in E('DIAL("SkyCloudLOD").note') and "smoothing" not in E('DIAL("SkyCloudLOD").note'), "SkyCloudLOD is cloud texture resolution; which value looks better stays unconfirmed")
check(E('DIAL("terrainMipLevel")[2]') == "Terrain blend detail" and "0 = full" in E('DIAL("terrainMipLevel").note'), "terrainMipLevel is Terrain blend detail, 0 = full")

done()
