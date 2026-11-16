"""More than one step back: today's steps (presets, restores, your own changes), newest first,
each with its own Back. Back on a step puts back the settings from just before it, and that step
and every newer one leave the list. Never a backup. /ec back goes back one step, the newest.

Run alone: python tests/test_back_history.py
"""
from lib import boot, chat, check, done

REG = """
for k, v in pairs({ bloomUserMult = "1", cameraFov = "90", Contrast = "57", Brightness = "46" }) do C_CVar.RegisterCVar(k, v) end
local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
mt.__index = function(t, k) if k == "GetText" then return function(self) return self.text end end return index(t, k) end
-- The day under test is set here, never the real one.
DAY = "2026-11-06"; HM = "10:40"
function date(f) return DAY .. " " .. HM end
"""

lua = boot()
lua.execute(REG)
lua.execute('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}')
E, X = lua.eval, lua.execute
lst = lambda t: [t[i] for i in range(1, len(t) + 1)] if t else []
NAMES = 'local t = {} for i, s in ipairs(NS.BackSteps()) do t[i] = NS.StepName(s) end return t'
names = lambda: lst(E('(function() %s end)()' % NAMES))
kinds = lambda: [s['kind'] for s in lst(E('NS.BackSteps()'))]
rows = lambda: E('#NS.ListBackups()')
g = lambda c: E('GetCVar("%s")' % c)

check(names() == [], "a fresh day has no steps")
n_rows = rows()

# Three presets: three steps, newest first, each saying when.
X('SetCVar("weatherDensity", "1"); HM = "10:41"; NS.ApplyPresetById("look:raid")')
w_after_raid = g("weatherDensity")
X('HM = "10:42"; NS.ApplyPresetById("tier1")')
X('HM = "10:43"; NS.ApplyPresetById("look:laptop")')
check(names() == ["Laptop", "Performance", "Raid & PvP"] and kinds() == ["preset"] * 3, "each preset is a step, newest first (%s)" % names())
check([s['time'] for s in lst(E('NS.BackSteps()'))] == ["10:43", "10:42", "10:41"], "each step says when it was")
check(rows() == n_rows, "steps are never backups: no backup rows added")
check(E('NS.BackSteps()[3].values.weatherDensity') == "1", "a step keeps the settings from just before it")

# Your own change since the newest step shows first, as its own step, not saved yet.
X('SetCVar("farclip", "1234")')
check(names()[0] == "Your own changes" and E('NS.BackSteps()[1].live') == True and len(names()) == 4, "a change of your own shows as the newest step")
check(E('#EyeCandyDB.steps') == 3, "and isn't saved until the next step")
# Its Back puts back what the newest step left, and keeps every step.
laptop_farclip = E('NS.BackSteps()[2].after.farclip')
n, line = E('NS.GoBack()')
check(n == 1 and line == "Back to before your own changes: 1 setting put back.", "Back on your own changes says what it did (%r)" % line)
check(g("farclip") == laptop_farclip and names() == ["Laptop", "Performance", "Raid & PvP"], "it puts back what Laptop left, and the steps stay")

# Your own change before the next preset is saved as a step between them.
X('SetCVar("farclip", "1234"); HM = "10:50"; NS.ApplyPresetById("tier3")')
check(names() == ["High", "Your own changes", "Laptop", "Performance", "Raid & PvP"], "your own changes are kept between presets (%s)" % names())
own = 'NS.BackSteps()[2]'
check(E(own + '.values.farclip') == laptop_farclip and E(own + '.after.farclip') == "1234" and E(own + '.time') == "10:43", "that step holds what Laptop left, and says it started after Laptop")
check(E('NS.StepLine(%s)' % own) == "Settings you changed yourself after 10:43.", "its grey line says so (%r)" % E('NS.StepLine(%s)' % own))
check(E('NS.StepLine(NS.BackSteps()[1])') == "Preset applied at 10:50.", "a preset's grey line says when")

# Back on an older step: settings from just before it come back, and it and every newer step go.
target = 'NS.BackSteps()[4]'  # Performance
count = E('NS.CountStepChanges(%s)' % target)
before_perf = E('NS.BackSteps()[4].values.farclip')
n, line = E('NS.GoBack(4)')
check(n == count and line.startswith("Back to before Performance: "), "Back on an older step changes what its count said (%s, %s)" % (n, count))
check(g("farclip") == before_perf and E('EyeCandyDB.look') == "raid", "settings and choices are as they were just before Performance")
check(names() == ["Raid & PvP"], "that step and every newer one leave the list")
check(E('NS.OnPreset().name') == "Raid & PvP", "and you are on the preset you were on before it")
check(rows() == n_rows, "going back adds no backup row")

# A restore is a step too, and its Back undoes it.
X('SetCVar("weatherDensity", "3"); B = NS.CreateBackup("manual", "Raid night"); SetCVar("weatherDensity", "1"); NS.ApplyPresetById("look:laptop")')
w_laptop = g("weatherDensity")
n_rows = rows()
X('HM = "11:00"; R = NS.RestoreBackupById(B.id)')
check(names()[0] == 'Restored "Raid night"' and kinds()[0] == "restore", "a restore is a step (%s)" % names())
check(E('NS.StepLine(NS.BackSteps()[1])') == "Backup restored at 11:00.", "its grey line says when")
check(rows() == n_rows and w_laptop != "3" and g("weatherDensity") == "3", "the restore worked and made no backup")
check(E('EyeCandyDB.onPreset') is None, "after a restore no preset of yours is the one you are on")
n, line = E('NS.GoBack()')
check(line.startswith('Back to before you restored "Raid night": '), "Back on a restore says so (%r)" % line)
check(g("weatherDensity") == w_laptop and E('NS.OnPreset().name') == "Laptop", "Back undoes the restore and puts you back on Laptop")

# Compare still means before your last preset, even after a restore.
X('NS.RestoreBackupById(B.id)')
check(E('NS.BeforeRecord().name') == "Laptop", "Compare's record is the newest preset, not the restore")
check(E('NS.ToggleCompare()') == True and E('NS.CompareLabel()') == "Showing: before Laptop", "Compare shows before Laptop")
check(names()[0] == 'Restored "Raid night"', "while Compare shows before, that is not your own change")
X('NS.StopCompare()')
check(names()[0] == 'Restored "Raid night"', "and ending Compare leaves nothing of your own")

# While Autotune has your settings, its changes are not yours.
X('SetCVar("farclip", "999"); EyeCandyDB.autotune = { before = {} }')
check(names()[0] != "Your own changes", "Autotune's changes are not shown as yours")
X('EyeCandyDB.autotune = nil')
check(names()[0] == "Your own changes", "once it is done, a change is yours again")

# /ec back goes back one step, the newest, and says so once.
X('CHAT = {}; SlashCmdList.EYECANDY("back")')
said = chat(lua)
check(len(said) == 1 and "Back to before your own changes: 1 setting put back." in said[0], "/ec back goes back one step, the newest (%s)" % said)

# In a fight Back changes nothing and keeps the steps.
before = names()
X('INCOMBAT = true; CHAT = {}; SlashCmdList.EYECANDY("back"); INCOMBAT = false')
said = chat(lua)
check(names() == before and len(said) == 1 and "in combat" in said[0], "in a fight Back says why and keeps every step (%s)" % said)

# At most ten saved steps: the oldest go.
for i in range(12):
    X('NS.ApplyPresetById("%s")' % ("tier1" if i % 2 else "tier2"))
check(E('#EyeCandyDB.steps') == 10 and E('NS.STEPS_MAX') == 10, "only the newest ten steps are kept")

# Kept for the day: tomorrow the list starts empty.
X('DAY = "2026-11-07"')
check(names() == [] and E('NS.BeforeRecord()') is None, "a new day starts with no steps")
X('CHAT = {}; SlashCmdList.EYECANDY("back")')
said = chat(lua)
check(len(said) == 1 and "Nothing to go back to today." in said[0], "and /ec back says there is nothing today (%s)" % said)
X('NS.ApplyPresetById("tier2")')
check(names() == ["Balanced"], "the new day's first preset is its first step (%s)" % names())

# Saved with EyeCandyDB: the steps survive a reload.
SER = """
function SER(v)
  if type(v) == "table" then
    local parts, k, x = {}, next(v)
    while k ~= nil do parts[#parts + 1] = "[" .. SER(k) .. "]=" .. SER(x); k, x = next(v, k) end
    return "{" .. table.concat(parts, ",") .. "}"
  elseif type(v) == "string" then return string.format("%q", v) end
  return tostring(v)
end
"""
X(SER)
X('SetCVar("farclip", "4444"); NS.ApplyPresetById("tier4")')
text = E('SER(EyeCandyDB)')
lua2 = boot(svdb='EyeCandyDB = ' + text)
lua2.execute(REG)
# The game keeps its settings over a reload; the stand-in starts fresh, so put them as they were.
lua2.execute('DAY = "2026-11-07"; for k, v in pairs(EyeCandyDB.steps[1].after) do SetCVar(k, v) end')
n2 = lst(lua2.eval('(function() %s end)()' % NAMES))
check(n2 == ["Ultra", "Your own changes", "Balanced"], "after a reload today's steps are still there (%s)" % n2)
lua2.execute('NS.GoBack(1)')
check(lua2.eval('GetCVar("farclip")') == "4444", "and Back still works on them")
check(lua2.eval('EyeCandyDB.lastBefore') is None, "there is no single Back record any more")

# An older version's single record moves into the list if it is from today, else it goes.
OLD = 'EyeCandyDB = { tiers = {}, keepApplied = true, lastBefore = { name = "Moody", label = "Before Moody", time = "2026-11-06 09:15", stamp = 3, values = { farclip = "4321" }, state = { tiers = { clarity = 2 } }, after = {} } }'
lua3 = boot(svdb=OLD)
lua3.execute(REG)
n3 = [s['name'] for s in lst(lua3.eval('NS.BackSteps()'))]
check(n3 == ["Moody"] and lua3.eval('NS.BackSteps()[1].time') == "09:15" and lua3.eval('EyeCandyDB.lastBefore') is None, "today's old record becomes a step (%s)" % n3)
lua3.execute('SlashCmdList.EYECANDY("back")')
check(lua3.eval('GetCVar("farclip")') == "4321" and lua3.eval('EyeCandyDB.tiers.clarity') == 2, "and Back on it puts its settings back")
lua4 = boot(svdb=OLD.replace("2026-11-06 09:15", "2026-11-05 22:00"))
lua4.execute(REG)
check(lua4.eval('#NS.BackSteps()') == 0 and lua4.eval('EyeCandyDB.lastBefore') is None, "an old record from another day goes")
lua5 = boot(svdb='EyeCandyDB = { tiers = {}, keepApplied = true, steps = { "junk", { kind = "preset", name = "X", day = "2026-11-06" } } }')
lua5.execute(REG)
check(lua5.eval('#NS.BackSteps()') == 0, "a damaged step is dropped")

# ---------------------------------------------------------------- the window
lua = boot()
lua.execute(REG)
lua.execute('FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}; SlashCmdList.EYECANDY("")')
E, X = lua.eval, lua.execute
P = 'EyeCandyMainFrame.pages.presets'
M = 'EyeCandyMainFrame'
A = 'EyeCandyAskFrame'


def headers():
    n = E('#%s.headers' % P)
    return [E('%s.headers[%d].label.text' % (P, i)) for i in range(1, n + 1) if E('%s.headers[%d].shown' % (P, i))]


def step_rows():
    n = E('#(%s.stepRows or {})' % P)
    return ['%s.stepRows[%d]' % (P, i) for i in range(1, n + 1) if E('%s.stepRows[%d].shown' % (P, i))]


check(headers()[0] == "Your presets" and step_rows() == [], "with no steps today there is no Today list")
check(E(P + '.backButton') is None, "and the card has no Back button of its own")

X('SetCVar("weatherDensity", "1"); NS.ApplyPresetById("look:raid"); NS.ApplyPresetById("look:laptop"); NS.RefreshUI()')
check(headers()[0] == "Today" and headers()[1] == "Your presets", "after a preset, Today comes first")
r = step_rows()
check(len(r) == 2 and E(r[0] + '.name.text') == "Laptop" and E(r[1] + '.name.text') == "Raid & PvP", "one row a step, newest first")
check(E(r[0] + '.line.text') == "Preset applied at 10:40." and E(r[0] + '.back.text') == "Back", "each row says what and when, and has its own Back")

# Back asks first, saying how many settings change and that newer steps go too.
X('%s.back.scripts.OnClick(%s.back)' % (r[1], r[1]))
t = E(A + '.textFS.text')
cnt = E('NS.CountStepChanges(NS.BackSteps()[2])')
check(E(A + '.shown') == True and E(A + '.accept.text') == "Back", "Back on a row asks first")
check(t.startswith("Put back your settings from just before Raid & PvP? This changes %d settings." % cnt) and "It also undoes the 1 newer step above it." in t, "the question says the count and what else goes (%r)" % t)
X(A + '.cancel.scripts.OnClick(%s.cancel)' % A)
check(len(step_rows()) == 2 and E('EyeCandyDB.look') == "laptop", "Cancel changes nothing")
X('%s.back.scripts.OnClick(%s.back)' % (r[1], r[1]))
X(A + '.accept.scripts.OnClick(%s.accept)' % A)
check(E('GetCVar("weatherDensity")') == "1" and step_rows() == [] and headers()[0] == "Your presets", "accepting goes back, and the list empties")
note = E(P + '.card.note.text')
check(note.startswith("|cff7cff7cBack to before Raid & PvP: ") and note.endswith(" put back.|r"), "the card says what Back put back, in green (%r)" % note)
check(not any("Back to before" in x for x in E('CHAT').values()), "and nothing goes to chat")
X('%s.hooks.OnHide(%s); NS.RefreshUI()' % (P, P))

# The newest step's question names no newer steps.
X('NS.ApplyPresetById("look:laptop"); NS.RefreshUI()')
r = step_rows()
X('%s.back.scripts.OnClick(%s.back)' % (r[0], r[0]))
check("newer" not in E(A + '.textFS.text'), "the newest step's question names no newer steps")
X(A + '.cancel.scripts.OnClick(%s.cancel)' % A)

# A change of your own shows within a second while the tab is open.
X('SetCVar("farclip", "1234")')
X('for i = 1, 11 do %s.scripts.OnUpdate(%s, 0.1) end' % (M, M))
r = step_rows()
check(E(r[0] + '.name.text') == "Your own changes" and E(r[0] + '.line.text') == "Settings you changed yourself after 10:40.", "your own change shows as a row within a second")

# In a fight Back says why on the card, in red, and changes nothing.
X('INCOMBAT = true; %s.back.scripts.OnClick(%s.back); %s.accept.scripts.OnClick(%s.accept); INCOMBAT = false' % (r[0], r[0], A, A))
refused = E(P + '.card.note.text')
check(refused.startswith("|cffff4040") and "combat" in refused and E('GetCVar("farclip")') == "1234", "Back in a fight says why on the card, in red (%r)" % refused)

# Only the newest three show, until Show all.
X('for i = 1, 5 do NS.ApplyPresetById(i % 2 == 0 and "tier1" or "tier2") end; NS.RefreshUI()')
total = E('#NS.BackSteps()')
check(len(step_rows()) == 3 and E(P + '.stepsMore.shown') == True and E(P + '.stepsMore.text') == "Show all %d" % total, "only the newest three show, with Show all (%s)" % E(P + '.stepsMore.text'))
X('%s.stepsMore.scripts.OnClick(%s.stepsMore)' % (P, P))
check(len(step_rows()) == total and E(P + '.stepsMore.text') == "Show fewer", "Show all shows every step today")
X('%s.stepsMore.scripts.OnClick(%s.stepsMore)' % (P, P))
check(len(step_rows()) == 3, "Show fewer goes back to three")

# Long names fit the row.
X('PID = NS.SaveCurrentAsPreset("A really long preset name for raids at night and more"); NS.ApplyPresetById(PID.id); NS.RefreshUI()')
r = step_rows()
check(E(r[0] + '.name.text').endswith("...") and E(r[0] + '.name.wordWrap') is not True, "a long name is cut, never wrapped (%r)" % E(r[0] + '.name.text'))

# Every promise of one step back is gone.
import glob, os
base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
texts = [open(f, encoding='utf-8').read() for f in glob.glob(os.path.join(base, 'EyeCandy', '*.lua'))]
texts += [open(os.path.join(base, f), encoding='utf-8').read() for f in ('README.md', 'CONTRIBUTING.md', os.path.join('docs', 'ui-rules.md'))]
bad = [p for p in ("One step back", "one step back", "only until you change something", "Back only works until",
                   "one step, until you change", "undo the last preset", "own backup holds") if any(p in t for t in texts)]
check(bad == [], "no file promises one step back any more (%s)" % bad)
done()
