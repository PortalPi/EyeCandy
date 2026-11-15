"""Standard tab text with a fixed width never wraps (rule 16), and the longest real label fits its
220px. Run: python tests/test_standard_labels.py"""
from lib import boot, check, done

PRE = """
WRAPS = {}
local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
local over = {
  SetWordWrap = function(self, v) self.wrap = v; if self.text then WRAPS[self.text] = v end end,
  SetWidth = function(self, w) self.width = w end,
}
mt.__index = function(t, k) if over[k] then return over[k] end return index(t, k) end
"""
STD = """
local reg = { gxMonitor="0", gxMaximize="1", useUiScale="0", uiscale="1", ffxAntiAliasingMode="4", cameraFov="90",
 graphicsShadowQuality="3", vsync="1", RenderScale="1", ResampleQuality="3" }
for k, v in pairs(reg) do C_CVar.RegisterCVar(k, v) end
"""
lua = boot(PRE)
lua.execute(STD)
lua.execute('FIRE("PLAYER_LOGIN"); SlashCmdList.EYECANDY(""); NS.ShowTab("standard"); NS.RefreshUI()')
E = lua.eval
n = E('#NS.stdRows')
check(n > 20, "the Standard tab built its rows (%d)" % n)
bad = E("""(function()
  local bad = {}
  for i, r in ipairs(NS.stdRows) do
    local name = tostring(r.def.cvar or r.def.key)
    if r.label.wrap ~= false then bad[#bad + 1] = name .. " label" end
    if r.valueText.wrap ~= false then bad[#bad + 1] = name .. " value" end
    if r.hint and r.hint.wrap ~= false then bad[#bad + 1] = name .. " hint" end
  end
  return table.concat(bad, ", ")
end)()""")
check(bad == "", "every row label, value and hint has word wrap off: %s" % bad)
check(E('WRAPS["The game\'s Graphics settings, in one place. They apply straight away."]') == False, "the intro line, which has the legend right under it, does not wrap")

# The longest label in this client, against the 220px it has. About 5.5px a character at the
# small font is a guess; 36 characters is 200px.
longest = E("""(function()
  local best, name = 0, ""
  for _, r in ipairs(NS.stdRows) do
    local t = r.label.text or ""
    if #t > best then best, name = #t, t end
  end
  return best .. "|" .. name
end)()""")
length, name = longest.split("|", 1)
check(int(length) <= 36, "the longest label fits its 220px: %s (%s characters)" % (name, length))

# An info row's value is cut to its width, so its tooltip gives it in full.
lua.execute("""
TIPS = {}
GameTooltip.SetOwner = function() TIPS = {} end
GameTooltip.AddLine = function(_, t) TIPS[#TIPS + 1] = t end
for _, r in ipairs(NS.stdRows) do if r.def.cvar == "gxMaximize" then INFO = r end; if r.def.cvar == "vsync" then TOG = r end end
INFO.scripts.OnEnter(INFO)
""")
tip = E('table.concat(TIPS, "\\n")')
check("Now: Fullscreen (Windowed)" in tip, "an info row's tooltip gives its whole value (%s)" % tip.replace("\n", " / "))
lua.execute('TIPS = {}; TOG.scripts.OnEnter(TOG)')
check("Now:" not in E('table.concat(TIPS, "\\n")'), "a control row's tooltip does not (its control already shows the value)")
done()
