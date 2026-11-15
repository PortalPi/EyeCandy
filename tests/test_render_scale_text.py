"""No text promises a render scale above 100% as fact. The game may cap render scale (a game update on
14 Nov 2026 stopped it at 100%), and Eye Candy clamps to what it allows, so any sentence naming a
figure above 100% says the game may allow less, or is about the cost above 100%.
Walks every level, setting and preset description, every Look tooltip, every preset row line, the
Showcase tooltip and Showcase's chat lines.
Run: python tests/test_render_scale_text.py"""
import re
from lib import boot, check, done

lua = boot()
E, X = lua.eval, lua.execute
X('FIRE("PLAYER_LOGIN")')

X('''
TEXTS = {}
local function add(where, s) if type(s) == "string" and s ~= "" then TEXTS[#TEXTS + 1] = where .. "\\1" .. s end end
for _, c in ipairs(NS.CATEGORIES) do add("level " .. tostring(c.name), c.desc) end
for _, ex in ipairs(NS.EXTRAS) do add("setting " .. tostring(ex.name), ex.desc) end
for _, p in ipairs(NS.LOOKS) do add("look " .. tostring(p.name), p.desc); add("look tooltip " .. tostring(p.name), NS.LookTooltip(p)) end
for _, p in ipairs(NS.SITUATIONS) do add("situation " .. tostring(p.name), p.desc) end
for _, p in ipairs(NS.ListPresets().builtin) do add("row line " .. tostring(p.name), NS.PresetLine(p)) end
for i = 1, #NS.TIERS + 1 do add("tier line " .. i, NS.PresetLine({ group = "Tiers", index = i })) end
add("Showcase tooltip", NS.ShowcaseTooltip())
''')
texts = [E('TEXTS[%d]' % i).split("\1", 1) for i in range(1, E('#TEXTS') + 1)]
kinds = {w.split(" ")[0] for w, _ in texts}
rows = [w for w, _ in texts if w.startswith("row line")]
check(len(rows) >= 9 and {"level", "setting", "look", "situation", "tier", "Showcase"} <= kinds,
      "the walk covers levels, settings, Looks and their tooltips, Situations, %d row lines, tier lines and Showcase" % len(rows))

# Showcase's chat lines, on a game that stops at 100%.
X('GetMaxRenderScale = function() return 1 end; C_CVar.RegisterCVar("RenderScale", "1"); CHAT = {}; NS.ApplyShowcase()')
for i in range(1, E('#CHAT') + 1):
    texts.append(("Showcase chat", E('CHAT[%d]' % i)))

PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s?%")
TIMES = re.compile(r"\b\d+(?:\.\d+)?\s?x\s+render scale", re.I)
SAFE = ("or the most the game allows", "highest render scale", "above 100%", "won't go above")


def promises(sentence):
    over = any(float(m) > 100 for m in PERCENT.findall(sentence))
    return over or "renders at" in sentence.lower() or TIMES.search(sentence) is not None


bad = []
for where, text in texts:
    for sentence in re.split(r"(?<=[.!?])\s+|\n", text):
        if promises(sentence) and not any(s in sentence.lower() for s in SAFE):
            bad.append((where, sentence.strip()))
check(not bad, "no sentence promises a render scale above 100%% as fact (%r)" % bad[:5])

# The rule itself catches the old wording.
old = ["Ultra renders at 125%, Cinematic at 150% (4K internal at 1440p).",
       "175% renders at 4480x2520, 200% at 5120x2880 (4 rendered pixels per screen pixel).",
       "Maximum clarity. 200% render scale with strong sharpening.",
       "Render scale 200%", "drop 'Render scale override' to 175% if it's too low.", "Set 2x render scale."]
missed = [s for s in old if not promises(s) or any(x in s.lower() for x in SAFE)]
check(not missed, "the check would catch each old sentence (%r)" % missed)

showcase = E('NS.PresetLine({ group = "Tiers", index = #NS.TIERS + 1 })')
check("highest render scale" in showcase and "200%" not in showcase, "the Showcase row line says highest render scale, not 200%% (%r)" % showcase)
crisp = E('NS.LookTooltip(NS.LOOKS[2])') if "Crisp" in E('NS.LOOKS[2].name') else next(t for w, t in texts if w == "look tooltip Crisp")
check("asks for 200%, or the most the game allows" in crisp, "Crisp's tooltip says it asks for 200%, or the most the game allows")
done()
