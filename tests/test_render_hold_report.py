"""/ec report shows the render scale hold: at load, now, and at the last logout (RenderCap.lua).
Run: python tests/test_render_hold_report.py"""
from lib import boot, check, done

CVAR = "ClientSettings_HIGH_MEM_FEATURES_BY_API_MASK"
HOLD = "16001,0x0,0x0,0x1ff"


def report(lua):
    lua.execute('SlashCmdList.EYECANDY("report")')
    return lua.eval('EyeCandyExportFrame.text')


def hold_line(rep):
    return next((l for l in rep.split("\n") if l.startswith("Render scale hold")), "")


# A start with the hold there, after a logout that cleared it: the servers wrote it back.
pre = ('C_CVar.RegisterCVar(%r, ""); SetCVar(%r, %r); EyeCandyDB = { renderHoldLogout = "cleared" }'
       % (CVAR, CVAR, HOLD))
lua = boot(pre)
lua.execute('FIRE("PLAYER_LOGIN")')
line = hold_line(report(lua))
check(CVAR in line, "the report has a line for the hold (%r)" % line)
check("when Eye Candy loaded set (" + HOLD + ")" in line, "it says the hold was there when Eye Candy loaded (%r)" % line)
check("at the last logout cleared" in line, "it says the last logout cleared it (%r)" % line)
check("cleared since /reload no" in line, "nothing cleared yet this session (%r)" % line)

lua.execute('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS()')
line = hold_line(report(lua))
check("now not set" in line and "cleared since /reload yes" in line, "after the clear it says now not set, cleared yes (%r)" % line)

# Logout: the result is kept for the next report.
lua.execute('SetCVar(%r, %r); FIRE("PLAYER_LOGOUT")' % (CVAR, HOLD))
check(lua.eval("EyeCandyDB.renderHoldLogout") == "cleared", "a logout that clears it records cleared")
lua.execute('FIRE("PLAYER_LOGOUT")')
check(lua.eval("EyeCandyDB.renderHoldLogout") == "was not set", "a logout with nothing to clear records was not set")

# A clear that does not stick is recorded as such.
lua.execute('SetCVar(%r, %r); local s = SetCVar; SetCVar = function(k, v) if k == %r then return end return s(k, v) end; FIRE("PLAYER_LOGOUT")'
            % (CVAR, HOLD, CVAR))
check(lua.eval("EyeCandyDB.renderHoldLogout") == "could not clear", "a clear that does not stick records could not clear")

# A first start: no hold, nothing recorded, and the report still builds.
lua2 = boot('C_CVar.RegisterCVar(%r, "")' % CVAR)
line = hold_line(report(lua2))
check("when Eye Candy loaded not set" in line and "at the last logout not recorded" in line,
      "with no hold and no record it says not set and not recorded (%r)" % line)
check("=== Eye Candy graphics export ===" in report(lua2), "the rest of the report is still there")

done()
