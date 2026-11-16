-- Eye Candy: the Hidden tab. Per-system tiers, Extras and fine control over hidden CVars the Graphics menu doesn't expose.
-- Every CVar here was confirmed present in the Forever client (build 70862) from an in-game export.
-- Groups are systems, in the order the Hidden tab shows them. tier = the ns.CATEGORIES key whose tier row heads the group.
-- Row: { cvar, label, min, max, step, note = "...", kind = "toggle" }
-- p = { Performance, Balanced, High, Ultra, Cinematic, Showcase }: what each preset sets.
--   nil = the preset hands the dial back (to its tier, your value from before Eye Candy, or the game default).
--   Only dials with a known 'better' direction get preset values.
-- Ranges are conservative; the client may clamp a value, and Eye Candy shows when it does.

local _, ns = ...

ns.ADVANCED = {
	{
		key = "clarity", tier = "clarity",
		note = "These settings only matter while Anti-Aliasing is set to CMAA 2.",
		rows = {
			{ "CMAA2Quality", "CMAA 2 quality", 0, 3, 1, note = "3 = highest." },
			{ "CMAA2ExtraSharpness", "CMAA 2 extra sharpness", kind = "toggle", p = { nil, nil, nil, nil, 1, 1 },  note = "Keeps more fine detail when smoothing edges." },
		},
	},
	{
		key = "image", name = "Image & Colour",
		note = "Normally in the Graphics menu. Set here, they override the menu (Eye Candy re-applies them after you close Options). Reset hands them back.",
		rows = {
			{ "Contrast", "Contrast", 0, 100, 1, note = "Menu range 0 to 100, default 50." },
			{ "Brightness", "Brightness", 0, 100, 1, note = "Menu range 0 to 100, default 50." },
			{ "Gamma", "Gamma", 0.3, 2.8, 0.05, note = "Menu range 0.3 to 2.8, default 1.0. Lower = deeper midtones and shadows." },
			{ "bloomUserMult", "Bloom intensity", 0, 1, 0.05, note = "Glow around bright light. Menu range 0 to 1. Guides suggest lower if the new glow feels washed out." },
			{ "cameraFov", "Field of view", 50, 90, 1, note = "90 is the game's maximum. Lower = less stretching at the screen edges and a more cinematic, telephoto feel." },
		},
	},
	{
		key = "lighting", tier = "lighting",
		rows = {
			{ "graphicsDepthEffects", "Depth effects (soft particles)", 0, 3, 1, tipKey = "OPTION_TOOLTIP_DEPTH_EFFECTS", note = "Soft particles: effects fade where they meet the ground and walls, not depth of field. 0 = off, 3 = high." },
			{ "entityShadowFadeScale", "Character shadow fade distance", 10, 200, 5, p = { 30, nil, nil, 100, 150, 200 },  note = "Probably higher = character shadows drawn further away. Unconfirmed: no documentation found." },
			{ "specular", "Specular highlights", 0, 1, 0.05, note = "How strong the shiny highlights on world surfaces are. 0 = none, 1 = full." },
			{ "componentSpecular", "Character specular", kind = "toggle", note = "Shiny highlights on characters and gear." },
			{ "componentEmissive", "Character glow (emissive)", kind = "toggle", note = "Glowing parts of gear and characters." },
		},
	},
	{
		key = "ao", name = "Ambient Occlusion",
		note = "These match Intel's ambient occlusion settings one for one (ranges below are Intel's). Unconfirmed which SSAO menu levels use them; Intel's adaptive mode is its top quality level.",
		rows = {
			{ "assaoRadius", "Radius", 0.5, 4, 0.025, note = "Intel: 'World (view) space size of the occlusion sphere.' Larger = broader shading; very large values give dark halos." },
			{ "assaoShadowMult", "Strength", 0.5, 2.5, 0.025, note = "Intel: 'Effect strength linear multiplier' (range 0 to 5). Higher = darker shading." },
			{ "assaoShadowPower", "Contrast", 0.5, 3, 0.01, note = "Intel: 'Effect strength pow modifier' (range 0.5 to 5). Higher = punchier, more contrasty shading." },
			{ "assaoSharpness", "Sharpness", 0, 1, 0.005, note = "Intel: how much the blur bleeds over object edges. 1 = not at all, 0.5 = half, 0 = ignores edges." },
			{ "assaoBlurPassCount", "Blur passes", 0, 6, 1, note = "Intel: edge-aware blur passes (0 to 6). More = smoother but loses fine detail, and costs more." },
			{ "assaoDetailShadowStrength", "Fine detail strength", 0, 5, 0.05, p = { nil, nil, nil, nil, nil, 0.5 }, note = "Intel: 'adds a lot of detail but also reduces temporal stability (adds aliasing)'. Intel's default is 0.5; high render scale hides the shimmer." },
			{ "assaoHorizonAngleThresh", "Horizon angle threshold", 0, 1, 0.025, note = "Intel: limits self-shadowing artefacts (range 0 to 0.2). Higher = less shading overall. WoW's default 0.4 is already above Intel's range." },
			{ "assaoFadeOutFrom", "Fade out from", 10, 500, 5, p = { nil, nil, nil, nil, 100, 150 },  note = "Distance where the shading starts fading." },
			{ "assaoFadeOutTo", "Fade out to", 50, 1000, 5, p = { nil, nil, nil, nil, 500, 800 },  note = "Distance where the shading is gone. Higher = visible further away." },
			{ "assaoAdaptiveQualityLimit", "Adaptive quality limit", 0, 1, 0.025, p = { nil, nil, nil, nil, 0.7, 1 }, note = "Intel: quality target for the adaptive (top) level, 0 to 1. Higher = more samples, better quality, more GPU cost." },
		},
	},
	{
		key = "atmosphere", tier = "atmosphere",
		rows = {
			{ "weatherDensity", "Weather density", 0, 3, 1, note = "Rain and snow amount. 3 = highest." },
			{ "volumeFogInterior", "Volumetric fog indoors", kind = "toggle", note = "Fog and light shafts inside buildings and caves." },
			{ "particulatesEnabled", "Ambient particulates", kind = "toggle", note = "Floating dust, pollen and motes in the air." },
		},
	},
	{
		key = "water", tier = "water",
		rows = {
			{ "reflectionMode", "Reflection mode", 0, 3, 1, note = "3 = highest." },
			{ "reflectionDownscale", "Downscaled reflections", kind = "toggle", note = "On = lower-resolution reflections. Off = full resolution." },
			{ "rippleDetail", "Ripple detail", 0, 2, 1, note = "2 = highest." },
		},
	},
	{
		key = "textures", tier = "textures",
		note = "Texture levels: 0 = full resolution. Yours are likely already at 0.",
		rows = {
			{ "terrainMipLevel", "Terrain blend detail", 0, 1, 1, note = "The detail of the map that blends ground textures together. 0 = full (best)." },
			{ "worldBaseMip", "World texture level", 0, 3, 1, note = "0 = full resolution (best)." },
			{ "componentTextureLevel", "Character texture level", 0, 2, 1, note = "0 = full resolution (best)." },
			{ "SkyCloudLOD", "Cloud texture resolution", 0, 1, 1, note = "The detail of the cloud textures. Which of 0 or 1 looks better is unconfirmed." },
		},
	},
	{
		key = "world", tier = "world",
		rows = {
			{ "farclip", "Far clip", 1000, 19600, 50, note = "Overall draw distance. The wiki lists 1000 to 19600. Above 10000 is untested in Forever; the status shows 'kept' if the game refuses." },
			{ "horizonClip", "Horizon clip", 1000, 10000, 50, note = "How far the low-detail horizon extends." },
			{ "horizonStart", "Horizon start", 400, 10000, 50, p = { nil, nil, nil, nil, nil, 10000 },  note = "Where the horizon fog begins. Higher = you see further before the fog. Very low values (100) bring fog right up close." },
			{ "cameraDistanceMaxZoomFactor", "Max camera zoom", 1, 4, 0.1, note = "How far out the camera can zoom. No graphics cost by itself." },
		},
	},
	{
		key = "distant", tier = "distant",
		note = "How far things keep full detail before swapping to simpler models or disappearing.",
		rows = {
			{ "doodadLodScale", "Tree/prop detail distance", 50, 500, 10, p = { nil, nil, nil, nil, nil, 500 },  note = "Higher = more detail." },
			{ "lodObjectFadeScale", "Small object fade distance", 50, 500, 10, p = { nil, nil, nil, nil, nil, 500 },  note = "Higher = small objects fade out further away." },
			{ "lodObjectCullSize", "Small object cull size", 0, 30, 1, p = { nil, nil, nil, nil, nil, 5 }, note = "Objects smaller than this get culled. Lower = less pop-in (players use 5). Confirmed." },
			{ "lodObjectCullDist", "Minimum cull distance", 0, 100, 5, p = { 20, nil, nil, 50, 75, 100 },  note = "Objects closer than this are never culled. Higher = less pop-in (players use 100). Confirmed." },
			{ "lodObjectMinSize", "Object min size", 0, 40, 1, p = { nil, nil, nil, 10, 5, 1 }, note = "Smallest object size that gets drawn. Lower = less pop-in (players use 1). Confirmed." },
			{ "lodObjectSizeScale", "Object size scale (culling)", 0.5, 3, 0.1, p = { 0.8, nil, nil, 1.5, 2, 3 },  note = "Higher = objects count as bigger, so they're culled later. Probably more detail." },
			{ "terrainLodDist", "Terrain detail distance", 200, 1500, 50, p = { nil, nil, nil, nil, nil, 1500 },  note = "Blizzard (old docs): 'Distance at which to render the lowest LOD for terrain. Will impact performance!' Higher = more detail." },
			{ "TerrainLodDiv", "Terrain detail divisor", kind = "choice", values = { 256, 512, 768, 1024, 2048 }, note = "Size of the terrain detail chunks. Old docs: powers of 2 only, 256 to 1024. Today's default (768) breaks that rule, so the docs may be outdated. Direction unconfirmed; the game's low-quality raid settings use 512. 2048 is beyond the documented range." },
			{ "wmoLodDist", "Building detail distance", 100, 1500, 50, p = { nil, nil, nil, nil, nil, 1500 },  note = "Probably higher = more detail. Unconfirmed." },
			{ "wmoLodDistScale", "Building detail scale", 0.5, 3, 0.1, p = { 0.8, nil, nil, 1.5, 2, 3 },  note = "Probably higher = more detail. Unconfirmed." },
			{ "wmoDoodadDist", "Building prop load distance", 500, 5000, 100, p = { 1000, nil, nil, 3000, 4000, 5000 },  note = "Higher = props in and around buildings load from further away." },
			{ "entityLodOffset", "Character detail offset", 0, 50, 1, note = "Direction unconfirmed. (Character detail distance itself is the setting above.)" },
			{ "dynamicLod", "Dynamic detail reduction", kind = "toggle", note = "On = the game lowers detail when under load. Off = steady detail." },
			{ "animFrameSkipLOD", "Skip animation frames at distance", kind = "toggle", p = { 1, nil, 0, 0, 0, 0 },  note = "On = distant animations run choppier to save CPU. Off = smooth." },
		},
	},
	{
		key = "foliage", tier = "foliage",
		rows = {
			{ "groundEffectDensity", "Grass density", 16, 256, 1, note = "Higher = thicker grass. 256 is the engine's limit." },
			{ "groundEffectDist", "Grass draw distance", 50, 500, 5, note = "Higher = grass further out. One of the bigger FPS costs." },
			{ "groundEffectFade", "Grass fade distance", 0, 510, 5, note = "Where grass starts fading out. At or above the grass draw distance = no fade: full grass right to the edge, then it stops. Lower = a gradual fade that starts sooner. Which looks better is taste." },
		},
	},
	{
		key = "effects", tier = "effects",
		rows = {
			{ "particleDensity", "Particle density %", 10, 100, 10, note = "Smoke, fire, sparks. 100 = all." },
			{ "particleMTDensity", "Multi-texture particle density %", 10, 100, 10, note = "Particles made of several textures. Which effects these are is not documented. 100 = all." },
			{ "DepthBasedOpacity", "Soft edges on effects", kind = "toggle", note = "Turns the soft edge effect on or off." },
			{ "showfootprintparticles", "Footprint particles", kind = "toggle", note = "Dust and splashes from footsteps." },
			{ "ffxGlow", "Full-screen glow", kind = "toggle", note = "Overall glow post-effect." },
			{ "ffxDeath", "Death screen effect", kind = "toggle", note = "The grey ghost-world effect when dead." },
		},
	},
	{
		key = "streaming", name = "Streaming",
		note = "How early the world loads in as you move. Changing these causes a short hitch while things reload.",
		rows = {
			{ "preloadStreamingDistObject", "Object streaming distance", 32, 256, 16, p = { nil, nil, nil, 128, 128, 256 },  note = "Higher = objects load in sooner while moving. Costs RAM, not FPS." },
			{ "preloadStreamingDistTerrain", "Terrain streaming distance", 128, 1024, 64, p = { nil, nil, nil, 512, 512, 1024 },  note = "Higher = terrain loads in sooner while moving." },
		},
	},
}

local categoryByKey = {}
for _, cat in ipairs(ns.CATEGORIES) do categoryByKey[cat.key] = cat end

local byCVar = {}
for _, group in ipairs(ns.ADVANCED) do
	if group.tier then
		group.category = categoryByKey[group.tier]
		group.name = group.name or (group.category and group.category.name) or group.key
	end
	for _, d in ipairs(group.rows) do
		byCVar[d[1]] = d
	end
end
ns.ADVANCED_BY_CVAR = byCVar

function ns.AdvancedCVars()
	local list = {}
	for _, group in ipairs(ns.ADVANCED) do
		for _, d in ipairs(group.rows) do
			list[#list + 1] = d[1]
		end
	end
	return list
end

----------------------------------------------------------------------
-- Logic
----------------------------------------------------------------------

local function Decimals(step)
	if not step or step >= 1 then return 0 end
	-- Places needed to write the step exactly: 0.1 -> 1, 0.05 -> 2, 0.025 -> 3, 0.005 -> 3.
	local places, s = 0, step
	while places < 4 and math.abs(s - math.floor(s + 0.5)) > 1e-9 do s = s * 10; places = places + 1 end
	return places
end

-- Nearest index in a choice dial's value list.
local function ChoiceIndex(d, v)
	local best, bestDiff = 1, math.huge
	for i, value in ipairs(d.values) do
		local diff = math.abs(value - (tonumber(v) or 0))
		if diff < bestDiff then best, bestDiff = i, diff end
	end
	return best
end

-- Snap to the dial's step (or nearest choice) and strip float noise (0.30000001 -> 0.3).
local function Snap(d, v)
	if d.kind == "choice" then
		return d.values[ChoiceIndex(d, v)]
	end
	local min, max, step = d[3], d[4], d[5]
	v = math.min(math.max(v, min), max)
	v = min + math.floor((v - min) / step + 0.5) * step
	return tonumber(string.format("%." .. Decimals(step) .. "f", v))
end
ns.SnapAdvanced = Snap

function ns.FormatAdvanced(d, v)
	if v == nil then return "?" end
	if d.kind == "toggle" then
		return ((tonumber(v) or 0) ~= 0) and "On" or "Off"
	end
	local n = tonumber(v)
	if not n then return tostring(v) end
	return string.format("%." .. Decimals(d[5]) .. "f", n)
end

-- The value a tier would set for this CVar right now, and the tier's row name.
function ns.TierValueFor(cvar)
	for _, cat in ipairs(ns.CATEGORIES) do
		local tier = ns.db.tiers[cat.key]
		for _, row in ipairs(cat.cvars) do
			if row[1] == cvar then
				if tier and tier > 0 and row[3][tier] ~= nil then
					return row[3][tier], cat.name
				end
				return nil, cat.name
			end
		end
	end
end

function ns.SetAdvanced(cvar, value)
	if InCombatLockdown() then
		-- The row says it when the window is open (rule 6, docs/ui-rules.md); chat only when it isn't.
		local win = _G.EyeCandyMainFrame
		local page = win and win.pages and win.pages.hidden
		if not (win and win:IsShown() and page and page:IsShown()) then ns.Print("can't change settings in combat.") end
		return false, "not changed in a fight"
	end
	ns.TakeBackup(false) -- captures the current value before the first change
	ns.db.advanced[cvar] = value
	SetCVar(cvar, value)
	return true
end

-- Hand the CVar back: to its tier if one sets it, else the value from before Eye Candy, else the game default.
-- In a fight nothing changes, not even your saved value, and it says why.
function ns.ResetAdvanced(cvar)
	if InCombatLockdown() then return false, "not changed in a fight" end
	ns.db.advanced[cvar] = nil
	local target = ns.TierValueFor(cvar)
	local original = ns.OriginalBackup()
	if target == nil and original and original.values then
		target = original.values[cvar]
	end
	if target == nil then
		local _, default = ns.GetInfo(cvar)
		target = default
	end
	if target ~= nil and ns.Exists(cvar) then
		SetCVar(cvar, target)
	end
	return true
end

function ns.ApplyAdvanced()
	local result = { applied = 0, skipped = {}, changed = {} }
	for cvar, value in pairs(ns.db.advanced) do
		local d = byCVar[cvar]
		ns.ApplyOne(cvar, d and d[2] or cvar, value, {}, result)
	end
	return result
end

ns.PRESET_NAMES = { "Performance", "Balanced", "High", "Ultra", "Cinematic", "Showcase" }

-- Set every dial for a preset (1 to 5 = tiers, 6 = Showcase). Values are applied by the next ApplyAll.
function ns.ApplyAdvancedPreset(index)
	for _, group in ipairs(ns.ADVANCED) do
		for _, d in ipairs(group.rows) do
			local v = d.p and d.p[index]
			if v ~= nil then
				ns.db.advanced[d[1]] = v
			elseif ns.db.advanced[d[1]] ~= nil then
				ns.ResetAdvanced(d[1])
			end
		end
	end
end

----------------------------------------------------------------------
-- Hidden tab
----------------------------------------------------------------------

local ROW_H = 26
local advRows, tierRows, extraRows = {}, {}, {}
ns.advRows, ns.tierRows, ns.extraRows = advRows, tierRows, extraRows
local hiddenPage

local helpMap
function ns.BlizzardHelp(cvar)
	if not helpMap then
		helpMap = {}
		if type(ConsoleGetAllCommands) == "function" then
			local ok, commands = pcall(ConsoleGetAllCommands)
			if ok and type(commands) == "table" then
				for _, c in ipairs(commands) do
					if c.command and c.help and c.help ~= "" then
						helpMap[c.command:lower()] = c.help
					end
				end
			end
		end
	end
	return helpMap[cvar:lower()]
end

local function TierLabel(tier)
	local colour = ns.TIER_COLOURS[tier or 0]
	local name = (tier and tier > 0) and ns.TIERS[tier] or "No change"
	return "|c" .. colour .. name .. "|r"
end

-- What a tier will set, for the tooltip.
local function TierPreview(cat, tier)
	local lines = { cat.desc, " " }
	if not tier or tier == 0 then
		lines[#lines + 1] = "|cff9d9d9dNo change: Eye Candy leaves these settings alone.|r"
	else
		lines[#lines + 1] = "|cffffd100" .. ns.TIERS[tier] .. " sets:|r"
		for _, row in ipairs(cat.cvars) do
			local v = row[3][tier]
			local now = ns.GetInfo(row[1])
			local value
			if now == nil then
				value = "|cff9d9d9dnot in this client|r"
			elseif ns.db.advanced[row[1]] ~= nil then
				value = "|cffffd100overridden by your setting (" .. tostring(ns.db.advanced[row[1]]) .. ")|r"
			elseif v == nil then
				value = "|cff9d9d9dunchanged|r"
			elseif row.scale and ns.db.extras.renderScale ~= nil then
				value = "|cffffd100overridden by your render scale (" .. math.floor(ns.db.extras.renderScale * 100 + 0.5) .. "%)|r"
			elseif row.scale then
				value = math.floor(ns.ClampRenderScale(v) * 100 + 0.5) .. "%"
			else
				value = ns.FormatNumber(v)
			end
			lines[#lines + 1] = row[2] .. ": " .. value .. ((now ~= nil) and ("  |cff9d9d9d(now " .. now .. ")|r") or "")
		end
	end
	lines[#lines + 1] = " "
	lines[#lines + 1] = "|cff9d9d9dPress Apply at the bottom after changing a level.|r"
	return table.concat(lines, "\n")
end

-- Blizzard's words for a setting: the Graphics menu's own tooltip when it has one (tipKey), else the
-- Standard tab's copy of it (which carries the English text if the client lacks the string), else the
-- CVar's help text.
function ns.BlizzardWords(cvar, tipKey)
	if tipKey then
		local menu = _G[tipKey]
		if type(menu) == "string" and menu ~= "" then return menu end
		local tip = ns.StandardTipText and ns.StandardTipText(cvar)
		if type(tip) == "string" and tip ~= "" then return tip end
	end
	return ns.BlizzardHelp(cvar)
end

local function RowTooltip(d)
	local lines = {}
	local _, default = ns.GetInfo(d[1])
	if d.kind == "choice" then
		local vals = {}
		for _, v in ipairs(d.values) do vals[#vals + 1] = ns.FormatAdvanced(d, v) end
		lines[#lines + 1] = "Choices: " .. table.concat(vals, ", ")
		lines[#lines + 1] = "Click the slider, then the mouse wheel moves it one step."
	elseif d.kind ~= "toggle" then
		lines[#lines + 1] = string.format("Range here: %s to %s, step %s", ns.FormatAdvanced(d, d[3]), ns.FormatAdvanced(d, d[4]), ns.FormatAdvanced(d, d[5]))
		lines[#lines + 1] = "Click the slider, then the mouse wheel moves it one step. Hold Shift for fine steps. Type a value and press Enter."
	end
	local parts = {}
	for i, name in ipairs(ns.PRESET_NAMES) do
		local v = d.p and d.p[i]
		parts[#parts + 1] = name .. " " .. (v ~= nil and ns.FormatAdvanced(d, v) or "-")
	end
	lines[#lines + 1] = "Presets: " .. table.concat(parts, ", ")
	if not d.p then lines[#lines + 1] = "|cff9d9d9dPresets hand this setting back (its 'better' direction isn't known).|r" end
	local _, owner = ns.TierValueFor(d[1])
	if owner then
		lines[#lines + 1] = "|cffffd100Overrides the " .. owner .. " level while set.|r"
	end
	lines[#lines + 1] = "|cff9d9d9dThe reset arrow hands it back to its level, or your value from before Eye Candy.|r"
	for i = 1, #lines do
		if not lines[i]:find("^|c") then lines[i] = "|cff9d9d9d" .. lines[i] .. "|r" end
	end
	return ns.SettingTip({
		quote = ns.BlizzardWords(d[1], d.tipKey), plain = d.note,
		default = default ~= nil and ns.FormatAdvanced(d, default) or nil,
		more = lines, cvar = d[1],
	})
end
ns.DialTooltip = RowTooltip

-- An Extra's tooltip, the same way: Blizzard's words, the plain line, the game default.
function ns.ExtraTooltip(ex)
	local _, default = ns.GetInfo(ex.cvar)
	-- The first line of desc is the plain line; the rest goes below the default.
	local desc = ex.desc or ""
	local plain, rest = desc:match("^([^\n]*)\n?(.*)$")
	local more = {}
	for line in (rest or ""):gmatch("[^\n]+") do more[#more + 1] = line end
	if ex.key == "resample" and ns.RenderScaleAbove100 and ns.RenderScaleAbove100(true) then
		more[#more + 1] = "|cffffd100Ignored now: render scale is above 100%, so the game uses Bicubic.|r"
	end
	more[#more + 1] = "|cff9d9d9dPress Apply after changing. '" .. ex.options[1][2] .. "' keeps whatever value is currently set.|r"
	if ex.slider then more[#more + 1] = "|cff9d9d9dType a value in the box, or use the arrows. Hold Shift for fine steps.|r" end
	local d = tonumber(default)
	local defaultText = default ~= nil and tostring(default) or nil
	if d and ex.slider and ex.slider.percent then defaultText = math.floor(d * 100 + 0.5) .. "%" end
	return ns.SettingTip({ quote = ns.BlizzardWords(ex.cvar, ex.tipKey), plain = plain, default = defaultText, more = more, cvar = ex.cvar })
end

local function RefreshRow(row)
	local d = row.d
	local value, default = ns.GetInfo(d[1])
	if value == nil then
		row.valueText:SetText("|cff9d9d9dn/a|r")
		row.status:SetText("|cff9d9d9dnot in client|r")
		if row.control then row.control:Hide(); row.valueText:Show() end
		if row.slider then row.slider:Hide() end
		if row.check then row.check:Hide() end
		row.dot:Hide()
		return
	end
	local n = tonumber(value)
	row.updating = true
	if d.kind == "toggle" then
		row.check:SetChecked((n or 0) ~= 0)
	elseif d.kind == "choice" and n then
		row.current = ChoiceIndex(d, n)
		row.slider:SetValue(row.current)
	elseif n then
		row.current = math.min(math.max(n, d[3]), d[4])
		row.slider:Refresh()
	end
	row.updating = false
	row.valueText:SetText(ns.FormatAdvanced(d, value))
	row.dot:SetShown(default ~= nil and not ns.Same(value, default))

	local override = ns.db.advanced[d[1]]
	local tierValue = ns.TierValueFor(d[1])
	if override ~= nil then
		if ns.Same(override, value) then
			row.status:SetText("|cffffd100custom|r")
		else
			row.status:SetText("|cffff4040kept " .. ns.FormatAdvanced(d, value) .. "|r")
		end
	elseif tierValue ~= nil then
		row.status:SetText("|cfffffffflevel|r")
	elseif ns.Same(value, default) then
		row.status:SetText("|cff9d9d9ddefault|r")
	else
		row.status:SetText("|cff9d9d9dmenu/game|r")
	end
	-- A change refused in a fight stays said on the row until the fight ends. Fights only: out of
	-- one the mark goes at once, so a refusal for any other reason would need its own clear.
	if row.refused then
		if InCombatLockdown() then row.status:SetText("|cffff4040" .. row.refused .. "|r") else row.refused = nil end
	end
end

-- The apply report from when each level or Extra was last changed. While it is still the newest
-- one, no Apply has tried the new choice yet, so the row is waiting (rule 4), not done or refused.
local tierEditedAt, extraEditedAt = {}, {}
local function Waiting(edited) return edited ~= nil and edited == (ns.lastReport or false) end

local function RefreshTierRow(row)
	local tier = ns.db.tiers[row.cat.key] or 0
	row.value:SetText(TierLabel(tier))
	local r = ns.lastReport and ns.lastReport[row.cat.key]
	if Waiting(tierEditedAt[row.cat.key]) then
		row.status:SetText("|cff9d9d9dnot applied yet. Press Apply.|r")
	elseif r then
		local status = r.applied .. " set"
		if r.notes > 0 then status = status .. ", |cffffd100" .. r.notes .. " note(s) in chat|r" end
		row.status:SetText(status)
	else
		row.status:SetText("")
	end
end

local function RefreshExtraRow(row)
	local value = ns.db.extras[row.ex.key]
	local waiting = Waiting(extraEditedAt[row.ex.key])
	local text = ns.ExtraLabel(row.ex, value)
	local r = ns.lastReport and ns.lastReport["extra:" .. row.ex.key]
	local now = ns.GetInfo(row.ex.cvar)
	local status, explained
	if row.slider then
		row.slider:Refresh()
		-- Grey box = not set by Eye Candy (the bar shows the value set now).
		if value == nil then row.slider.box:SetTextColor(0.616, 0.616, 0.616) else row.slider.box:SetTextColor(1, 0.82, 0) end
		-- Format takes a bar value, so a real value goes through In first (Sharpness runs backwards).
		local function Show(v)
			v = tonumber(v)
			if not v then return nil end
			local t = row.slider.Format(row.slider.In(v))
			return (t == "Off" or not row.ex.slider.percent) and t or (t .. "%")
		end
		local nowText = Show(now) or tostring(now)
		if value == nil then
			status = text .. ", now " .. nowText
		elseif waiting and not (tonumber(now) and ns.Same(tonumber(now), value)) then
			status = "|cff9d9d9dnot applied yet, now " .. nowText .. ". Press Apply.|r"
		elseif tonumber(now) and not ns.Same(tonumber(now), value) then
			-- An Apply tried it and the game kept its own value. Say it here, not only in chat. Render scale above
			-- 100% is held until a restart (RenderCap.lua lifts the hold for the next start): say that instead.
			local held = row.ex.cvar == "RenderScale" and tonumber(value) > tonumber(now)
				and ns.RenderCap and ns.RenderCap.Held()
			status = "|cffff4040" .. (held and ns.RenderCap.HELD or ("the game kept " .. nowText)) .. "|r"
			explained = true
		else
			status = "now " .. nowText
		end
	else
		row.value:SetText(value == nil and ("|cff9d9d9d" .. text .. "|r") or ("|cffffd100" .. text .. "|r"))
		status = "now " .. tostring(now)
		if value ~= nil and waiting and not ns.Same(now, value) then
			status = "|cff9d9d9dnot applied yet, now " .. tostring(now) .. ". Press Apply.|r"
		end
		-- The resample filter only matters below 100%: above it the game uses Bicubic.
		if row.ex.key == "resample" and ns.RenderScaleAbove100 and ns.RenderScaleAbove100(true) then
			row.value:SetText("|cff9d9d9d" .. text .. "|r")
			status = "|cff9d9d9dignored above 100% render scale (the game uses Bicubic)|r"
			row.ignored = true
		else
			row.ignored = false
		end
	end
	-- The refusal is one note, said on the row. Any other note still needs chat.
	if r and r.notes > (explained and 1 or 0) then status = status .. ", |cffffd100see chat|r" end
	row.status:SetText(status)
	row.dot:SetShown(ns.IsChanged(row.ex.cvar) == true)
end

function ns.RefreshAdvanced()
	if not (hiddenPage and hiddenPage:IsShown()) then return end
	for _, row in ipairs(tierRows) do RefreshTierRow(row) end
	for _, row in ipairs(extraRows) do RefreshExtraRow(row) end
	for _, row in ipairs(advRows) do RefreshRow(row) end
	-- The fight's over: the "can't reset" line goes, like the rows' fight lines.
	if hiddenPage.resetRefused and not InCombatLockdown() then
		hiddenPage.resetRefused = nil
		hiddenPage.resetResult:SetText("")
	end
end
ns.TAB_REFRESH.hidden = ns.RefreshAdvanced

local function Commit(row, value)
	local ok, err = ns.SetAdvanced(row.d[1], value)
	row.refused = (not ok) and err or nil
	RefreshRow(row) -- in combat this snaps the control back to the real value, and says why in red
end

local function MakeSlider(row, d)
	local s = CreateFrame("Slider", nil, row, "BackdropTemplate")
	s:SetOrientation("HORIZONTAL")
	s:SetSize(190, 16)
	if BACKDROP_SLIDER_8_8 then s:SetBackdrop(BACKDROP_SLIDER_8_8) end
	s:SetThumbTexture("Interface\\Buttons\\UI-SliderBar-Button-Horizontal")
	local isChoice = d.kind == "choice"
	-- A choice dial slides over positions 1..n of its value list.
	local min, max, step = d[3], d[4], d[5]
	if isChoice then min, max, step = 1, #d.values, 1 end
	s:SetMinMaxValues(min, max)
	s:SetValueStep(step)
	s:SetObeyStepOnDrag(true)
	s:SetScript("OnValueChanged", function(_, v)
		if row.updating then return end
		if isChoice then
			local idx = math.min(math.max(math.floor(v + 0.5), 1), #d.values)
			row.current = idx
			v = d.values[idx]
		else
			v = Snap(d, v)
			row.current = v
		end
		row.valueText:SetText(ns.FormatAdvanced(d, v))
		-- Debounce: apply once the slider settles, not on every pixel of a drag.
		row.token = (row.token or 0) + 1
		local token = row.token
		C_Timer.After(0.25, function()
			if token == row.token then Commit(row, v) end
		end)
	end)
	-- As ns.Slider: the wheel steps only after a click on the bar, so scrolling the list past it is safe.
	local function Arm(on) s.armed = on; s:EnableMouseWheel(on) end
	Arm(false)
	s:HookScript("OnMouseDown", function() Arm(true) end)
	s:HookScript("OnLeave", function() Arm(false) end)
	s:SetScript("OnMouseWheel", function(self, delta)
		if not self.armed then return end
		if isChoice then
			self:SetValue(math.min(math.max((row.current or 1) + delta, 1), #d.values))
		else
			self:SetValue(Snap(d, (row.current or d[3]) + delta * d[5]))
		end
	end)
	return s
end

local function RowBase(content, index)
	local row = CreateFrame("Frame", nil, content)
	row:SetSize(ns.ROW_W, ROW_H - 2)
	local bg = row:CreateTexture(nil, "BACKGROUND")
	bg:SetAllPoints()
	bg:SetColorTexture(1, 1, 1, (index % 2 == 0) and 0.04 or 0.0)
	row.dot = ns.Dot(row)
	return row
end

local function BuildDialRow(content, d, index)
	local row = RowBase(content, index)
	row.d = d

	local label = ns.Label(row, d[2], "GameFontHighlightSmall")
	label:SetPoint("LEFT", 12, 0)
	label:SetWidth(220)
	label:SetWordWrap(false) -- rule 16: a long name is cut, the full one is in the tooltip
	row.label = label

	if d.kind == "toggle" then
		row.check = CreateFrame("CheckButton", nil, row, "UICheckButtonTemplate")
		row.check:SetSize(24, 24)
		row.check:SetPoint("LEFT", 236, 0)
		row.check:SetScript("OnClick", function(self)
			Commit(row, self:GetChecked() and 1 or 0)
		end)
	elseif d.kind == "choice" then
		row.slider = MakeSlider(row, d)
		row.slider:SetPoint("LEFT", 240, 0)
	else
		-- A numeric dial: the shared slider with arrows, a typed box and a tick at the game default.
		local holder = CreateFrame("Frame", nil, row)
		holder:SetSize(244, 20)
		holder:SetPoint("LEFT", 236, 0)
		row.slider = ns.Slider(holder, {
			min = d[3], max = d[4], step = d[5], width = 150, reset = false,
			get = function() return tonumber((ns.GetInfo(d[1]))) end,
			set = function(v) Commit(row, v) end,
			default = function() local _, def = ns.GetInfo(d[1]); return tonumber(def) end,
		})
		row.slider:SetPoint("LEFT", 22, 0)
		row.control = holder
	end

	row.valueText = row:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
	row.valueText:SetPoint("LEFT", 436, 0)
	row.valueText:SetWidth(42)
	row.valueText:SetJustifyH("RIGHT")
	if row.control then row.valueText:Hide() end -- the typed box shows the value

	-- The reset arrow hands the dial back (tier, your value from before Eye Candy, or the game default).
	row.reset = ns.ResetArrow(row, function()
		local ok, err = ns.ResetAdvanced(d[1])
		row.refused = (not ok) and err or nil
		RefreshRow(row)
	end, "Hands this setting back: to its level if one sets it, else your value from before Eye Candy, else the game default.")
	row.reset:SetPoint("LEFT", 484, 0)

	row.status = row:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall")
	row.status:SetPoint("LEFT", 506, 0)
	row.status:SetPoint("RIGHT", -4, 0)
	row.status:SetJustifyH("LEFT")

	row:EnableMouse(true)
	ns.Tooltip(row, d[2], function() return RowTooltip(d) end)

	advRows[#advRows + 1] = row
	return row
end

-- A "< value >" stepper row, used for tiers and Extras.
local function StepperRow(content, index, text, onStep)
	local row = RowBase(content, index)
	-- Names are white (rule 20) and never wrap (rule 16); the tooltip has the full name.
	row.label = ns.Label(row, text, "GameFontHighlight")
	row.label:SetPoint("LEFT", 12, 0)
	row.label:SetWidth(220)
	row.label:SetWordWrap(false)
	local minus = ns.Button(row, "<", 24, function() onStep(-1) end)
	minus:SetPoint("LEFT", 236, 0)
	row.value = row:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
	row.value:SetPoint("LEFT", minus, "RIGHT", 4, 0)
	row.value:SetWidth(110)
	local plus = ns.Button(row, ">", 24, function() onStep(1) end)
	plus:SetPoint("LEFT", row.value, "RIGHT", 4, 0)
	row.status = row:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall")
	row.status:SetPoint("LEFT", plus, "RIGHT", 8, 0)
	row.status:SetPoint("RIGHT", -4, 0)
	row.status:SetJustifyH("LEFT")
	row:EnableMouse(true)
	-- The wheel steps only after a click on the row, so scrolling the list past it is safe.
	local function Arm(on) row.armed = on; row:EnableMouseWheel(on) end
	Arm(false)
	row:HookScript("OnMouseDown", function() Arm(true) end)
	row:HookScript("OnLeave", function() Arm(false) end)
	row:SetScript("OnMouseWheel", function(_, delta)
		if row.armed then onStep(delta > 0 and 1 or -1) end
	end)
	return row
end

local function StepTier(cat, dir)
	local t = (ns.db.tiers[cat.key] or 0) + dir
	if t < 0 then t = #ns.TIERS end
	if t > #ns.TIERS then t = 0 end
	ns.db.tiers[cat.key] = (t > 0) and t or nil
	tierEditedAt[cat.key] = ns.lastReport or false
	ns.SaveMirror()
	ns.RefreshUI()
end
ns.StepTier = StepTier

local function StepExtra(ex, dir)
	local current = ns.db.extras[ex.key]
	local idx = 1
	for i, opt in ipairs(ex.options) do
		if (opt[1] == nil and current == nil) or (opt[1] ~= nil and current ~= nil and ns.Same(opt[1], current)) then
			idx = i
		end
	end
	idx = idx + dir
	if idx < 1 then idx = #ex.options end
	if idx > #ex.options then idx = 1 end
	ns.db.extras[ex.key] = ex.options[idx][1]
	extraEditedAt[ex.key] = ns.lastReport or false
	ns.SaveMirror()
	ns.RefreshUI()
end
ns.StepExtra = StepExtra

-- Set an Extra to a value (nil = "Use tier" / "Leave as is"). Applies when you press Apply, like the stepper.
local function SetExtra(ex, value)
	ns.db.extras[ex.key] = value
	extraEditedAt[ex.key] = ns.lastReport or false
	ns.SaveMirror()
	ns.RefreshUI()
end
ns.SetExtra = SetExtra

-- A numeric Extra as a slider. While it is "Use tier" / "Leave as is" the bar shows the value set now.
-- The reset arrow goes back to that, not to a number.
local function ExtraSliderRow(content, index, ex)
	local row = RowBase(content, index)
	row.label = ns.Label(row, ex.name, "GameFontHighlight")
	row.label:SetPoint("LEFT", 12, 0)
	row.label:SetWidth(220)
	row.label:SetWordWrap(false)
	local sp = ex.slider
	local lo, hi = sp.min, sp.max
	if ex.scale then
		lo = (type(GetMinRenderScale) == "function" and GetMinRenderScale()) or 0.33
		hi = (type(GetMaxRenderScale) == "function" and GetMaxRenderScale()) or 2
	end
	local holder = CreateFrame("Frame", nil, row)
	holder:SetSize(266, 20)
	holder:SetPoint("LEFT", 236, 0)
	row.slider = ns.Slider(holder, {
		min = lo, max = hi, step = sp.step, off = sp.off, invert = sp.invert, percent = sp.percent, width = 150,
		get = function()
			local v = ns.db.extras[ex.key]
			if v == nil then v = tonumber((ns.GetInfo(ex.cvar))) end
			return tonumber(v)
		end,
		set = function(v) SetExtra(ex, v) end,
		default = function() local _, d = ns.GetInfo(ex.cvar); return tonumber(d) end,
		onReset = function() SetExtra(ex, nil) end,
		resetTip = "Back to '" .. ex.options[1][2] .. "': Eye Candy stops setting this.",
	})
	row.slider:SetPoint("LEFT", 22, 0)
	row.control = holder
	row.status = row:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall")
	row.status:SetPoint("LEFT", 506, 0)
	row.status:SetPoint("RIGHT", -4, 0)
	row.status:SetJustifyH("LEFT")
	row:EnableMouse(true)
	return row
end

ns.TAB_BUILD.hidden = function(page)
	hiddenPage = page
	-- Which settings wait for Apply is said here once (rule 4); a row says "not applied yet" while it waits.
	local waits = {}
	for _, ex in ipairs(ns.EXTRAS) do waits[#waits + 1] = ex.name end
	local last = table.remove(waits)
	local named = #waits > 0 and (table.concat(waits, ", ") .. " and " .. last) or last
	local intro = ns.Label(page, "Settings the game's menu doesn't show. Most change at once, over the level above them. "
		.. "Levels wait for the Apply button" .. (named and (", and so do " .. named) or "") .. ".\n|cffffd100custom|r = set by you   |cfffffffflevel|r = set by a level   |cffff4040kept|r = the game refused it   |TInterface\\Buttons\\WHITE8X8:6:6:0:0:8:8:0:8:0:8:255:209:0|t = changed from the game default", "GameFontNormalSmall")
	intro:SetPoint("TOPLEFT", 4, -2)
	intro:SetWidth(ns.PAGE_W - 172)
	page.intro = intro

	-- Reset all: click twice within 3 seconds.
	local resetAll
	resetAll = ns.Button(page, "Reset hidden settings", 160, function()
		if resetAll.armed then
			resetAll.armed = false
			resetAll:SetText("Reset hidden settings")
			-- In combat the game won't take the values back, so nothing is reset (rule 9: refused is red).
			if InCombatLockdown() then
				page.resetResult:SetText("|cffff4040Can't reset in a fight.|r")
				page.resetRefused = true
				return
			end
			local names = {}
			for cvar in pairs(ns.db.advanced) do names[#names + 1] = cvar end
			for _, cvar in ipairs(names) do ns.ResetAdvanced(cvar) end
			-- The result shows under the button (rule 6), not in chat. It goes when you leave the tab.
			page.resetResult:SetText(#names == 0 and "|cff9d9d9dNothing to reset.|r"
				or string.format("Reset %d %s.", #names, #names == 1 and "setting" or "settings"))
			ns.RefreshUI()
		else
			page.resetResult:SetText("")
			resetAll.armed = true
			resetAll:SetText("|cffff4040Click to confirm|r")
			C_Timer.After(3, function()
				if resetAll.armed then
					resetAll.armed = false
					resetAll:SetText("Reset hidden settings")
				end
			end)
		end
	end)
	resetAll:SetPoint("TOPRIGHT", -2, 0)
	page.resetAll = resetAll
	page.resetResult = ns.Label(page, "", "GameFontHighlightSmall")
	page.resetResult:SetPoint("TOPRIGHT", resetAll, "BOTTOMRIGHT", 0, -2)
	page.resetResult:SetWidth(160)
	page.resetResult:SetJustifyH("RIGHT")
	page.resetResult:SetWordWrap(false)
	page:HookScript("OnHide", function() page.resetResult:SetText("") end)
	ns.Tooltip(resetAll, "Reset hidden settings", "Hands back every setting here that changes at once: to its level, or your value from before Eye Candy. Levels and the settings that wait for Apply stay as they are. Click twice to confirm.")

	-- The list starts under the intro, however many lines it wraps to (one line is about 12px).
	local introH = tonumber(intro.GetStringHeight and intro:GetStringHeight()) or 36
	page.listTop = math.max(40, math.ceil(introH) + 2 + 8)
	local content = ns.ScrollPage(page, -page.listTop)
	local list = ns.NewList(content)
	ns.TAB_LIST.hidden = list
	local index = 0
	for _, group in ipairs(ns.ADVANCED) do
		local header, h = ns.Header(content, group.name, group.note)
		local headerItem = list:Add(header, h, group.name)
		local cat = group.category
		if cat then
			index = index + 1
			local row = StepperRow(content, index, cat.name .. " level", function(dir) StepTier(cat, dir) end)
			row.cat = cat
			ns.Tooltip(row, cat.name, function() return TierPreview(cat, ns.db.tiers[cat.key]) end)
			tierRows[#tierRows + 1] = row
			local words = { cat.name, "level tier" }
			for _, r in ipairs(cat.cvars) do words[#words + 1] = r[2]; words[#words + 1] = r[1] end
			list:Add(row, ROW_H, table.concat(words, " "), headerItem)
		end
		for _, ex in ipairs(ns.EXTRAS) do
			if ex.system == group.key then
				index = index + 1
				local row = ex.slider and ExtraSliderRow(content, index, ex)
					or StepperRow(content, index, ex.name, function(dir) StepExtra(ex, dir) end)
				row.ex = ex
				ns.Tooltip(row, ex.name, function() return ns.ExtraTooltip(ex) end)
				extraRows[#extraRows + 1] = row
				list:Add(row, ROW_H, ex.name .. " " .. ex.cvar, headerItem)
			end
		end
		for _, d in ipairs(group.rows) do
			index = index + 1
			local row = BuildDialRow(content, d, index)
			list:Add(row, ROW_H, d[2] .. " " .. d[1], headerItem)
		end
	end
end
