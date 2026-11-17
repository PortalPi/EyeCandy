"""Checks for /ec report (EyeCandy/Report.lua). Run: python tests/test_report.py"""
from lib import boot, chat, check, done, toc_files

HANDLER = 'geterrorhandler()'
ADDON = r'Interface\\AddOns\\EyeCandy\\Core.lua'
OTHER = r'Interface\\AddOns\\Other\\Thing.lua'


def report(lua):
    lua.execute('SlashCmdList.EYECANDY("report")')
    return lua.eval('EyeCandyExportFrame.text')


def fire(lua, msg):
    lua.execute(HANDLER + '("' + msg + '")')


# Capture must be in place before the other files load, so load-time errors are seen.
files = toc_files()
check(files.index('Report.lua') < files.index('Core.lua'), "Report.lua loads before Core.lua in the .toc")

lua = boot()
rep = report(lua)
check("=== Eye Candy bug report ===" in rep and "Addon: Eye Candy 1.0.0-test" in rep, "report starts with the addon version")
check("Client: 1.60.1 (70790)" in rep and "=== Eye Candy graphics export ===" in rep and "--- Eye Candy tiers ---" in rep, "report holds game build and the current settings")
check("(none caught)" in rep, "report says when no errors were caught")
check(any("Bug report ready" in x for x in chat(lua)), "report tells the player to copy it")
check("CurseForge" in lua.eval('EyeCandyExportFrame.hint.text'), "the report's box says it can go on GitHub or CurseForge")
lua.execute('SlashCmdList.EYECANDY("find shadow")')
check("GitHub" not in lua.eval('EyeCandyExportFrame.hint.text'), "a find result's box only says how to copy")
lua.execute('SlashCmdList.EYECANDY("export")')
check("CurseForge" in lua.eval('EyeCandyExportFrame.hint.text'), "the settings export's box says where it can go")

fire(lua, ADDON + ':123: attempt to index a nil value')
fire(lua, ADDON + ':123: attempt to index a nil value')
rep = report(lua)
check("[2x]" in rep and "attempt to index a nil value" in rep and "(none caught)" not in rep, "an error that mentions Eye Candy is listed once with a count")
check(lua.eval('ERRSEEN') == 2, "the game's own error handler still gets every error")

# Another addon's error: our wrapper's own frames are on its stack but must not make it ours.
lua.execute(r'DEBUGSTACK = "[string \"@Interface\\AddOns\\EyeCandy\\Report.lua\"]:40: in function <x>\n[C]: in function `pcall\39"')
fire(lua, OTHER + ':9: unrelated failure')
rep = report(lua)
check("unrelated failure" not in rep, "other addons' errors are left out, even with our wrapper on their stack")

# A look-alike file name is not our wrapper.
lua.execute(r'DEBUGSTACK = "[string \"@Interface\\AddOns\\BugReport.lua\"]:12: in function <z>"')
fire(lua, OTHER + ':9: lookalike failure')
check("lookalike failure" not in report(lua), "BugReport.lua is not mistaken for Report.lua (error still not ours)")

# An error that only passes through Eye Candy is kept, with the stack, minus our wrapper.
lua.execute(r'DEBUGSTACK = "[string \"@Interface\\AddOns\\EyeCandy\\Report.lua\"]:40: in function <x>\n[C]: in function `pcall\39\n[string \"@Interface\\AddOns\\EyeCandy\\UI.lua\"]:77: in function <y>"')
fire(lua, OTHER + ':9: called from us')
rep = report(lua)
check("called from us" in rep and "UI.lua" in rep, "an error whose stack passes through Eye Candy is listed, with the stack")
check("Report.lua" not in rep.split("--- Lua errors")[1].split("=== Eye Candy graphics export")[0], "our own wrapper's lines and pcall lines are cut from the stack")

# Long stacks are cut to 6 lines.
lines = "\\n".join('[string \\"@Interface\\\\AddOns\\\\EyeCandy\\\\UI.lua\\"]:%d: in function <f%d>' % (i, i) for i in range(1, 15))
lua.execute('DEBUGSTACK = "' + lines + '"')
fire(lua, OTHER + ':9: deep failure')
rep = report(lua)
check("<f6>" in rep and "<f7>" not in rep, "a long stack is cut to 6 lines")
lua.execute('DEBUGSTACK = ""')

# Only the newest 10 distinct errors, each cut short.
lua.execute(r'for i = 1, 12 do geterrorhandler()("Interface\\AddOns\\EyeCandy\\Core.lua:" .. i .. ": failure number " .. i) end')
lua.execute(r'geterrorhandler()("Interface\\AddOns\\EyeCandy\\Core.lua:1: " .. string.rep("x", 2000))')
kept = lua.eval('#NS.CapturedErrors()')
check(kept == 10, "only the newest 10 errors are kept (%d)" % kept)
rep = report(lua)
check("Core.lua:12: failure number 12" in rep and "Core.lua:2: failure number 2" not in rep and "Core.lua:3: failure number 3" not in rep, "oldest errors drop off first")
check("x" * 601 not in rep and "x" * 500 in rep, "a long message is cut to 600 characters")

# Secret values are never touched.
luaS = boot()
luaS.execute('SECRET = "Interface\\\\AddOns\\\\EyeCandy\\\\Core.lua:5: hidden"; function issecretvalue(v) return v == SECRET end')
luaS.execute('geterrorhandler()(SECRET)')
luaS.execute('geterrorhandler()("Interface\\\\AddOns\\\\EyeCandy\\\\Core.lua:6: visible")')
check(luaS.eval('#NS.CapturedErrors()') == 1 and luaS.eval('ERRSEEN') == 2, "a secret error message is skipped, passed on, and nothing breaks")
luaS.execute('geterrorhandler()(nil); geterrorhandler()({})')
check(luaS.eval('#NS.CapturedErrors()') == 1, "a non-text error is ignored without raising")

# A client without the error handler functions: the report still builds and says so.
luaN = boot(svdb='geterrorhandler = nil; seterrorhandler = nil')
repN = report(luaN)
check("error capture is off" in repN and "=== Eye Candy graphics export ===" in repN, "no error handler API: report still builds and says capture is off")

# The report says whether our wrapper is still the game's error handler and how many errors it got.
luaC = boot()
check("still the game's error handler: yes. Errors it was given: 0 (0 unreadable)." in report(luaC), "check line: handler is ours, nothing seen yet")
fire(luaC, OTHER + ':9: not ours')
fire(luaC, ADDON + ':1: ours')
check("Errors it was given: 2 (0 unreadable)." in report(luaC), "check line counts errors that do not mention Eye Candy too")
luaC.execute('seterrorhandler(function() end)')
check("still the game's error handler: NO." in report(luaC), "check line says NO when another addon replaced the handler")
luaU = boot()
luaU.execute('function issecretvalue(v) return v == "hidden" end')
luaU.execute('geterrorhandler()("hidden")')
check("Errors it was given: 1 (1 unreadable)." in report(luaU), "check line counts unreadable errors")

# Help text.
lua.execute('SlashCmdList.EYECANDY("help")')
check(any("/ec report" in x for x in chat(lua)), "help lists /ec report")

done()
