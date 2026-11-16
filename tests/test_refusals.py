"""A refusal shows in the window, in red, next to what failed; chat stays for slash commands
and for a closed window (docs/ui-rules.md rule 6). Presets card, Backups tab, bottom bar.
Run: python tests/test_refusals.py"""
from lib import boot, chat, check, done

PRE = """
local cf = CreateFrame
function CreateFrame(kind, name, parent, template) local f = cf(kind, name, parent, template); f.parent = parent; return f end
UIParent = CreateFrame("Frame", "UIParent"); UIParent.shown = true
WorldFrame = CreateFrame("Frame", "WorldFrame"); WorldFrame.shown = true
function SetUIVisibility(v) UIParent.shown = v and true or false; if v and UIParent.hooks.OnShow then UIParent.hooks.OnShow(UIParent) end end
local mt = getmetatable(CreateFrame("Frame")); local index = mt.__index
mt.__index = function(t, k)
  if k == "GetText" then return function(self) return self.text end end
  return index(t, k)
end
"""
RED = "|cffff4040"
HELPERS = """function ACCEPT(text) if text then EyeCandyAskFrame.edit.text = text end EyeCandyAskFrame.accept.scripts.OnClick(EyeCandyAskFrame.accept) end
function CLICK(b) b.scripts.OnClick(b) end"""

lua = boot(PRE)
E, X = lua.eval, lua.execute
X(HELPERS)
X('FIRE("PLAYER_LOGIN"); FIRE("PLAYER_ENTERING_WORLD", true, false); RUNTIMERS(); CHAT = {}; NS.ShowTab("presets")')
M = 'EyeCandyMainFrame'
P = M + '.pages.presets'
B = M + '.pages.backups'

# --- Presets card: a refused Duplicate, Share, Rename, Delete and Save say it on the card's line.
X('NS.DuplicatePreset = function() return nil, "Too many presets." end')
X('NS.PresetAction({ id = "x", name = "Mine" }, "duplicate")')
check(E(P + '.card.note.text') == RED + "Too many presets.|r" and not chat(lua), "a refused Duplicate says why in red on the card, not in chat")
X('NS.ExportPreset = function() return nil, "Sharing needs the game\'s encoding tools." end')
X('NS.PresetAction({ id = "x", name = "Mine" }, "share")')
check("encoding tools" in E(P + '.card.note.text') and RED in E(P + '.card.note.text') and not chat(lua), "a refused Share says why on the card")
# A name box that refused its name stays open and says why under it, in red (rule 6).
ASK = 'EyeCandyAskFrame'
X('NS.RenamePreset = function() return nil, "That name is taken." end; NS.PresetAction({ id = "x", name = "Mine" }, "rename"); ACCEPT("Other")')
check(E(ASK + '.shown') and E(ASK + '.errFS.text') == RED + "That name is taken.|r" and E(ASK + '.errFS.shown')
      and E(ASK + '.edit.text') == "Other" and not chat(lua), "a refused Rename keeps the box open, the name still in it, and says why under it in red")
X('NS.RenamePreset = function() return true end; ACCEPT("Other")')
check(not E(ASK + '.shown'), "a name that works closes it")
X('NS.PresetAction({ id = "x", name = "Mine" }, "rename"); ACCEPT("")')
check(E(ASK + '.shown') and "Type a name" in E(ASK + '.errFS.text'), "an empty name is refused in the box too")
X('NS.PresetAction({ id = "x", name = "Mine" }, "rename")')
check(E(ASK + '.errFS.text') == "" and not E(ASK + '.errFS.shown'), "the next question starts with no red line")
X('NS.Ask({ title = "T", text = "Q", accept = "OK", onAccept = function() return true end }); ACCEPT()')
check(not E(ASK + '.shown'), "an answer that returns true (not a reason) closes the box as before")
X('NS.DeletePreset = function() return nil, "Built-in presets stay." end; NS.PresetAction({ id = "x", name = "Mine" }, "delete")')
check(E(ASK + '.accept.text') == RED + "Delete|r", "Delete's confirm button is red (rule 15)")
X('ACCEPT()')
check("stay" in E(P + '.card.note.text') and not E(ASK + '.shown') and not chat(lua), "a refused Delete (nothing typed) closes and says why on the card")
X('NS.PresetAction({ id = "x", name = "Mine" }, "rename")')
check(E(ASK + '.accept.text') == "Rename", "Rename's button is not red")
X(ASK + ':Hide()')
X('NS.SaveCurrentAsPreset = function() return nil, "Beautiful is a built-in name. Pick another." end; CLICK(%s.saveButton); ACCEPT("Beautiful")' % P)
check(E(ASK + '.shown') and "built-in name" in E(ASK + '.errFS.text') and E(P + '.card.note.text') == "" and not chat(lua),
      "a refused Save keeps the name box open and says why under it, not on the card")
X(ASK + ':Hide()')
X('NS.DuplicatePreset = function() return nil, "Too many presets." end; NS.PresetAction({ id = "x", name = "Mine" }, "duplicate"); NS.ExportPreset = function() return "code" end; NS.PresetAction({ id = "x", name = "Mine" }, "share")')
check(E(P + '.card.note.text') == "", "a Share that works clears an older refusal at once")
X('NS.DuplicatePreset = function() return true end; NS.PresetAction({ id = "x", name = "Mine" }, "duplicate")')
check(E(P + '.card.note.text') == "", "the next action that works clears the old refusal")
X('NS.DuplicatePreset = function() return nil, "Too many presets." end; NS.PresetAction({ id = "x", name = "Mine" }, "duplicate")')
X('NS.ShowTab("backups"); %s.hooks.OnHide(%s); NS.ShowTab("presets")' % (P, P))
check(E(P + '.card.note.text') == "", "leaving the tab clears the refusal")

# --- Window closed: chat is fine.
X('%s:Hide()' % M)
X('NS.PresetAction({ id = "x", name = "Mine" }, "duplicate")')
check(any("Too many" in m for m in chat(lua)), "with the window closed a refusal still goes to chat")
X('NS.ShowTab("presets")')

# --- Create backup: on the bar from any tab but Backups, on Backups' own line there.
X('NS.CreateBackup = function() return nil, "Can\'t back up in combat." end')
X('CLICK(%s.createBackup); ACCEPT("")' % M)
check(E(M + '.barMsg.text') == RED + "Can't back up in combat.|r" and not chat(lua), "the bar's Create backup says why in red above the bar, not in chat")
X('NS.ShowTab("backups")')
check(E(M + '.barMsg.text') == "", "changing tab clears the bar's line")
X('NS.AskCreateBackup(); ACCEPT("")')
check(E(B + '.result.text') == RED + "Can't back up in combat.|r" and E(M + '.barMsg.text') == "" and not chat(lua), "on the Backups tab the refusal goes on its own result line")
X('NS.ShowTab("hidden")')

# --- Compare and Peek.
X('CLICK(%s.compare)' % M)
check("Nothing to compare yet" in E(M + '.barMsg.text') and RED in E(M + '.barMsg.text') and not chat(lua), "Compare with nothing to compare says why above the bar")
X('INCOMBAT = true; %s.peek.scripts.OnClick(%s.peek)' % (M, M))
check("Can't hide the screen in combat" in E(M + '.barMsg.text') and not chat(lua), "Peek in combat replaces the line with its own reason")
X('INCOMBAT = false')
X('CHAT = {}')
X('SlashCmdList.EYECANDY("compare")')
check(any("Nothing to compare" in m for m in chat(lua)), "/ec compare keeps printing to chat")

# --- Shrunk bar: the window grows a line for it, and shrinks back when it clears.
X('NS.ShowTab("presets"); NS.ToggleShrink(); %s.compare.scripts.OnClick(%s.compare, "LeftButton")' % (M, M))
check("Nothing to compare" in E(M + '.barMsg.text'), "the shrunk bar shows the line too")
X('NS.ToggleShrink()')
check(E(M + '.barMsg.text') == "", "opening the window up clears it")

# --- Apply with nothing to apply.
X('NS.ShowTab("hidden"); CHAT = {}; CLICK(%s.apply)' % M)
check("nothing to apply" in E(M + '.barMsg.text') and RED in E(M + '.barMsg.text') and not chat(lua), "Apply with nothing to apply says so above the bar, not in chat")
X('SlashCmdList.EYECANDY("apply")')
check(any("nothing to apply" in m for m in chat(lua)), "/ec apply keeps printing to chat")
X('NS.db.tiers.clarity = 2; CHAT = {}; CLICK(%s.apply)' % M)
check(E(M + '.barMsg.text') == "" and any("applied" in m for m in chat(lua)), "an Apply that does something clears the line and still reports to chat")
done()
