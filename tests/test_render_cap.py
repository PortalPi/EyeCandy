"""The game's 100% hold on render scale (16 Nov 2026): Eye Candy clears it for the next start.
Run: python tests/test_render_cap.py"""
from lib import boot, chat, check, done

CVAR = "ClientSettings_HIGH_MEM_FEATURES_BY_API_MASK"
HOLD = "16001,0x0,0x0,0x1ff"
# The servers' line, and a game that holds render scale at 100% this session.
PRE = 'C_CVar.RegisterCVar(%r, ""); SetCVar(%r, %r); MAXSCALE = 1; function GetMaxRenderScale() return MAXSCALE end' % (CVAR, CVAR, HOLD)

lua = boot(PRE)
E, X = lua.eval, lua.execute
X('FIRE("PLAYER_LOGIN"); FIRE("PLAYER_ENTERING_WORLD", true, false)')
check(E("GetCVar(%r)" % CVAR) == HOLD, "nothing is cleared at once: the servers may still be sending it")
X("RUNTIMERS()")
check(E("GetCVar(%r)" % CVAR) == "", "a few seconds after a loading screen the hold is cleared for the next start")
X("SetCVar(%r, %r)" % (CVAR, HOLD))
X('FIRE("PLAYER_LOGOUT")')
check(E("GetCVar(%r)" % CVAR) == "", "written back during the session, it is cleared again at logout")
check(E("NS.RenderCap.Held()") is True, "the game holds 100% this session")

# What the player reads while it is held.
X("CHAT = {}; NS.ApplyShowcase()")
msgs = chat(lua)
check(any("Showcase on" in m and "restart" in m and "200%" in m for m in msgs), "Showcase says to restart the game for 200%% (%r)" % msgs)
check(any("Render scale" in m and "held at 100% until you restart the game" in m for m in msgs),
      "the note on render scale says it is held until a restart, not just the most the game allows (%r)" % msgs)

# The Hidden tab's render scale row, refused while held, and refused with 200% allowed.
X('C_CVar.RegisterCVar("RenderScale", "1"); SlashCmdList.EYECANDY(""); NS.ShowTab("hidden")')
X('function EXROW(key) for _, r in ipairs(NS.extraRows) do if r.ex.key == key then return r end end end')
X('NS.db.extras.renderScale = 1.75; SetCVar("RenderScale", "1"); NS.RefreshUI()')
s = E('EXROW("renderScale").status.text') or ""
check("held at 100% until you restart the game" in s and "ff4040" in s, "the Hidden tab's row says, in red, it is held until a restart (%r)" % s)
X("MAXSCALE = 2")
check(E("NS.RenderCap.Held()") is False, "after a restart, with 200% allowed, nothing says it is held")
X("NS.RefreshUI()")
s = E('EXROW("renderScale").status.text') or ""
check("the game kept 100%" in s and "restart" not in s, "a refusal with 200%% allowed says only what the game kept (%r)" % s)

# A loading screen just before a fight: the clear waits for the fight to end.
X("MAXSCALE = 1; SetCVar(%r, %r); INCOMBAT = true" % (CVAR, HOLD))
X('FIRE("PLAYER_ENTERING_WORLD", false, false); RUNTIMERS()')
check(E("GetCVar(%r)" % CVAR) == HOLD, "nothing is changed in a fight")
X('INCOMBAT = false; FIRE("PLAYER_REGEN_ENABLED")')
check(E("GetCVar(%r)" % CVAR) == "", "it is cleared once the fight ends")

# A game with no such line: nothing to clear, no error, and a 100% top isn't called the hold.
lua2 = boot("")
lua2.execute('FIRE("PLAYER_LOGIN"); FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); FIRE("PLAYER_LOGOUT")')
check(lua2.eval("ERRSEEN") == 0 and lua2.eval("NS.RenderCap.Clear()") is False, "with no such line there is nothing to clear, and no error")
lua2.execute("function GetMaxRenderScale() return 1 end")
check(lua2.eval("NS.RenderCap.Held()") is False, "a 100% top with no hold set is not called the hold")

done()
