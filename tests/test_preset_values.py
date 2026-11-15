"""ns.PresetValues(id) gives every value a preset sets without applying it: built-ins worked out,
yours as saved, as a copy. An unknown id gives nil. Autotune starts from a preset this way.
Run: python tests/test_preset_values.py"""
from lib import boot, check, done

lua = boot()
E, X = lua.eval, lua.execute
X('C_CVar.RegisterCVar("Contrast", "50"); FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}')

# A built-in: the values it would set, and nothing is applied or recorded.
X('BEFORE_LOOK = EyeCandyDB.look; BEFORE_BACK = NS.db.backTo; M = NS.PresetValues("look:moody")')
check(E('type(M)') == "table" and E('M.Contrast') == "62", "a built-in Look gives its values (Moody's contrast is %r)" % E('M and M.Contrast'))
check(E('GetCVar("Contrast")') == "50", "and nothing is applied")
check(E('EyeCandyDB.look == BEFORE_LOOK and NS.db.backTo == BEFORE_BACK'), "and no Look or Back to before record is set")
X('A = NS.PresetValues("look:moody"); B = NS.PresetValues("look:moody")')
check(E('A ~= B'), "each call gives a fresh table")

# The values are what applying it asks for: each one the game sets, or one it says it kept less of.
X('n = 0; for _ in pairs(M) do n = n + 1 end')
check(E('n') > 20, "a built-in sets many values (%d)" % E('n'))
X('CHAT = {}; NS.ApplyPresetById("look:moody")')
X('MISMATCH = {}; for cvar, v in pairs(M) do if v ~= nil and GetCVar(cvar) ~= nil and tostring(GetCVar(cvar)) ~= tostring(v) then MISMATCH[#MISMATCH + 1] = cvar .. "=" .. tostring(v) end end')
said = " ".join(E('CHAT[%d]' % i) for i in range(1, E('#CHAT') + 1))
unexplained = [m for m in (E('MISMATCH[%d]' % i) for i in range(1, E('#MISMATCH') + 1)) if ("asked " + m.split("=")[1]) not in said]
check(not unexplained, "applying Moody sets each value PresetValues gave, or says the game kept less (%r)" % unexplained)

# Yours, as saved, and the copy can't change the saved preset.
X('P = NS.SaveCurrentAsPreset("Mine"); V = NS.PresetValues(P.id)')
check(E('V.Contrast') == E('P.values.Contrast') and E('V ~= P.values'), "your preset gives its saved values, as a copy")
X('V.Contrast = "1"')
check(E('P.values.Contrast') != "1", "changing the copy leaves the saved preset alone")

X('U1, U2 = NS.PresetValues("no-such-id")')
check(E('U1') is None and E('U2') == "missing", "an unknown id gives nil and \"missing\"")

# A tier and Showcase go through their own code (the tier steps, the Showcase extras).
X('T3 = NS.PresetValues("tier3"); SH = NS.PresetValues("tier" .. (#NS.TIERS + 1))')
X('nt = 0; for _ in pairs(T3) do nt = nt + 1 end; ns_ = 0; for _ in pairs(SH) do ns_ = ns_ + 1 end')
check(E('nt') > 20 and E('ns_') > 20, "a tier and Showcase give their values (%d, %d)" % (E('nt'), E('ns_')))
X('''
SI = #NS.TIERS + 1; DIALED = {}
for _, g in ipairs(NS.ADVANCED or {}) do for _, d in ipairs(g.rows) do if d.p and d.p[SI] ~= nil then DIALED[d[1]] = true end end end
EXTRA_OK = true; NX = 0
for _, ex in ipairs(NS.EXTRAS) do
  local v = NS.SHOWCASE_EXTRAS[ex.key]
  if v ~= nil and not DIALED[ex.cvar] then NX = NX + 1; if SH[ex.cvar] ~= tostring(v) then EXTRA_OK = ex.key end end
end
if NX == 0 then EXTRA_OK = "none checked" end
''')
check(E('EXTRA_OK') is True, "Showcase holds its extras (first wrong: %r)" % E('EXTRA_OK'))

# Duplicate now uses it: a copy of a built-in holds every value the built-in gives.
X('D = NS.DuplicatePreset("look:moody"); SAME = true; nd = 0; for k, v in pairs(D.values) do nd = nd + 1; if M[k] ~= v then SAME = false end end; for _ in pairs(M) do nd = nd - 1 end')
check(E('SAME') and E('nd') == 0, "Duplicate of Moody holds exactly Moody's values")
X('P.desc = "Tested in Dalaran."; D2 = NS.DuplicatePreset(P.id)')
check(E('D2.desc') == "Tested in Dalaran.", "Duplicate of yours still copies its note")

# Yours with no values (only a hand-edited saved file): said, not an empty preset.
X('P.values = nil; B1, B2 = NS.PresetValues(P.id); DD1, DD2 = NS.DuplicatePreset(P.id)')
check(E('B1') is None and E('B2') == "damaged", "yours with no values gives nil and \"damaged\"")
check(E('DD1') is None and "damaged" in str(E('DD2')), "and Duplicate refuses it instead of making an empty copy (%r)" % E('DD2'))
done()
