"""A setting refused in a fight says so on its own row, in red, not in chat (docs/ui-rules.md rule 6):
Standard rows, the game-menu button, Hidden dial rows.
Run: python tests/test_refusals_rows.py"""
from lib import boot, chat, check, done

SETUP = """
local reg = { graphicsShadowQuality="3", vsync="1", RenderScale="1", componentSpecular="1", cameraFov="90", maxFPS="60", useMaxFPS="1" }
for k, v in pairs(reg) do C_CVar.RegisterCVar(k, v) end
function SettingsPanel:Open() self.shown = true end
function STDROW(cvar) for _, r in ipairs(NS.stdRows) do if r.def.cvar == cvar then return r end end end
function ADVROW(cvar) for _, r in ipairs(NS.advRows) do if r.d[1] == cvar then return r end end end
function CLICK(b) b.scripts.OnClick(b) end
-- The harness's checkboxes always say ticked; this one says unticked, so a click asks for "0".
function UNTICK(b) b.GetChecked = function() return false end end
"""
RED = "|cffff4040"

lua = boot()
E, X = lua.eval, lua.execute
X(SETUP)
X('FIRE("PLAYER_LOGIN"); SlashCmdList.EYECANDY(""); NS.ShowTab("standard"); NS.RefreshUI(); CHAT = {}')
S = 'EyeCandyMainFrame.pages.standard'

# Standard row: a toggle in a fight.
X('INCOMBAT = true; local r = STDROW("vsync"); UNTICK(r.check); CLICK(r.check)')
check(E('STDROW("vsync").valueText.text') == RED + "not changed in a fight|r", "a Standard toggle refused in a fight says so on its row, in red")
check(E('GetCVar("vsync")') == "1" and not chat(lua), "the setting did not change and nothing went to chat")
# Another refusal (the master slider refreshes every row), a bar button, a tab change: still the fight.
X('NS.RefreshUI(); NS.RefreshStandard()')
check(E('STDROW("vsync").valueText.text') == RED + "not changed in a fight|r", "the line stays through other refreshes while the fight is on")
X('INCOMBAT = false; FIRE("PLAYER_REGEN_ENABLED")')
check(E('STDROW("vsync").valueText.text') == "", "the row's line goes when the fight ends")
X('CLICK(STDROW("vsync").check)')
check(E('GetCVar("vsync")') == "0" and E('STDROW("vsync").valueText.text') == "", "out of a fight the same click changes it and says nothing")

# The tab not in front when the fight ends: the next fight doesn't show the old line.
X('INCOMBAT = true; local r = STDROW("vsync"); UNTICK(r.check); CLICK(r.check); NS.ShowTab("hidden")')
X('INCOMBAT = false; FIRE("PLAYER_REGEN_ENABLED"); INCOMBAT = true; NS.ShowTab("standard"); NS.RefreshUI()')
check(E('STDROW("vsync").valueText.text') == "", "a line from the last fight doesn't come back in the next one")
X('INCOMBAT = false; FIRE("PLAYER_REGEN_ENABLED"); SetCVar("vsync", "0")')

# A range row's own checkbox (Max Foreground FPS's on/off) in a fight.
X('INCOMBAT = true; CHAT = {}; local r = STDROW("maxFPS"); UNTICK(r.checkBox); CLICK(r.checkBox)')
check(E('STDROW("maxFPS").valueText.text') == RED + "not changed in a fight|r" and E('GetCVar("useMaxFPS")') == "1" and not chat(lua), "a range row's checkbox refused in a fight says so on its row")
X('INCOMBAT = false; FIRE("PLAYER_REGEN_ENABLED")')
check(E('STDROW("maxFPS").valueText.text') == "", "and it goes when the fight ends")

# Window closed: chat is fine.
X('EyeCandyMainFrame:Hide(); INCOMBAT = true; CHAT = {}')
check(E('(NS.SetStandard("vsync", "1"))') == False and any("in a fight" in m for m in chat(lua)), "with the window closed it still goes to chat")
X('INCOMBAT = false; NS.ShowTab("standard")')

# The game-menu button.
X('CHAT = {}; INCOMBAT = true; CLICK(%s.gameMenu)' % S)
check(RED in E(S + '.gameMenuMsg.text') and "fight" in E(S + '.gameMenuMsg.text') and not E('SettingsPanel.shown') and not chat(lua), "the game-menu button says why under itself in a fight")
X('INCOMBAT = false; CLICK(%s.gameMenu)' % S)
check(E(S + '.gameMenuMsg.text') == "" and E('SettingsPanel.shown') == True, "out of a fight it opens and the line is gone")
X('SettingsPanel.shown = false; EyeCandyMainFrame:Show(); INCOMBAT = true; CLICK(%s.gameMenu)' % S)
X('%s.hooks.OnHide(%s)' % (S, S))
check(E(S + '.gameMenuMsg.text') == "", "leaving the tab clears it")
X('INCOMBAT = false')

# Hidden dial row.
X('NS.ShowTab("hidden"); NS.RefreshUI(); CHAT = {}')
X('INCOMBAT = true; local r = ADVROW("componentSpecular"); UNTICK(r.check); CLICK(r.check)')
check(E('ADVROW("componentSpecular").status.text') == RED + "not changed in a fight|r" and not chat(lua), "a Hidden dial refused in a fight says so on its row, in red")
check(E('EyeCandyDB.advanced.componentSpecular') is None, "and the dial did not change")
X('NS.RefreshUI(); NS.RefreshAdvanced()')
check(E('ADVROW("componentSpecular").status.text') == RED + "not changed in a fight|r", "the line stays through other refreshes while the fight is on")
X('INCOMBAT = false; FIRE("PLAYER_REGEN_ENABLED")')
check("not changed" not in E('ADVROW("componentSpecular").status.text'), "the row's line goes when the fight ends")

# The reset arrow in a fight: nothing changes, your value is kept, and the row says why.
X('NS.SetAdvanced("componentSpecular", "0"); NS.RefreshAdvanced(); INCOMBAT = true; CHAT = {}; CLICK(ADVROW("componentSpecular").reset)')
check(E('EyeCandyDB.advanced.componentSpecular') == "0" and E('GetCVar("componentSpecular")') == "0", "the reset arrow in a fight keeps your value and the game's")
check(E('ADVROW("componentSpecular").status.text') == RED + "not changed in a fight|r" and not chat(lua), "and the row says why, in red")
X('INCOMBAT = false; FIRE("PLAYER_REGEN_ENABLED"); CLICK(ADVROW("componentSpecular").reset)')
check(E('EyeCandyDB.advanced.componentSpecular') is None and "not changed" not in E('ADVROW("componentSpecular").status.text'), "after the fight the arrow hands it back")
# The Hidden tab not in front (a slider's delayed commit after a tab change): chat says it.
X('INCOMBAT = true; CHAT = {}; NS.ShowTab("presets")')
check(E('(NS.SetAdvanced("componentSpecular", 0))') == False and any("in a fight" in m for m in chat(lua)), "a refusal with its tab not in front goes to chat, not nowhere")
X('INCOMBAT = false; NS.ShowTab("standard"); INCOMBAT = true; CLICK(%s.gameMenu); FIRE("PLAYER_REGEN_ENABLED")' % S)
check(E(S + '.gameMenuMsg.text') == "", "the game-menu line goes when the fight ends")
X('INCOMBAT = false')
done()
