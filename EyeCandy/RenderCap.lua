-- Eye Candy: lifts the game's 100% hold on render scale.
--
-- Since the game patch of 14 Nov 2026, Blizzard's servers write ClientSettings_HIGH_MEM_FEATURES_BY_API_MASK
-- into the game's config (Config.wtf) every session, and GetMaxRenderScale() then says 1 (100%). The game reads
-- it once, when it starts. Cleared with SetCVar and the game restarted, render scale goes up to 200% again, at
-- the character screen and in the world (checked in game, 16 Nov 2026). The servers write it back during
-- a session (the same Config.wtf had it again that day), so Eye Candy clears it at every logout, and again a few
-- seconds after each loading screen in case the game closes without a logout (a crash or Alt+F4).
--
-- Always on, with no box to tick (the maintainer's choice, 16 Nov 2026). Its name means "high-memory features":
-- Blizzard may have held it for memory reasons. That is a guess; nothing public says why.

local _, ns = ...
local RC = {}
ns.RenderCap = RC

RC.CVAR = "ClientSettings_HIGH_MEM_FEATURES_BY_API_MASK"
RC.AFTER_LOAD = 10 -- seconds after a loading screen, once the servers have had time to send it

local function IsSet()
	local v = GetCVar(RC.CVAR)
	return v ~= nil and v ~= ""
end

-- Clears the hold for the next start. Returns true when it was set and is now cleared.
function RC.Clear()
	if not IsSet() then return false end
	if not pcall(SetCVar, RC.CVAR, "") or IsSet() then return false end
	RC.cleared = true
	return true
end

-- True while the game holds render scale at 100% this session (until it restarts): the top is 100%
-- and the hold was there (set now, or cleared by Eye Candy since this /reload). A 100% top with no
-- hold has some other cause, so nothing says a restart lifts it. After a /reload in a held session
-- this is false, and the lines say "the most the game allows now", which is still true.
function RC.Held()
	if type(GetMaxRenderScale) ~= "function" then return false end
	local ok, hi = pcall(GetMaxRenderScale)
	if not (ok and tonumber(hi) ~= nil and tonumber(hi) <= 1) then return false end
	return RC.cleared == true or IsSet()
end

-- What the player reads when render scale is held: why, and what to do.
RC.HELD = "held at 100% until you restart the game"
RC.TELL = "The game holds render scale at 100% until you restart it. After a restart it can go up to 200%."

-- Never in a fight: a setting the game guards in combat would show a "blocked" warning that pcall
-- can't stop. A clear due in a fight waits for it to end.
local events = CreateFrame("Frame")
local function ClearSoon()
	if InCombatLockdown() then
		pcall(events.RegisterEvent, events, "PLAYER_REGEN_ENABLED")
	else
		RC.Clear()
	end
end
events:SetScript("OnEvent", function(_, event)
	if event == "PLAYER_LOGOUT" then
		RC.Clear()
	elseif event == "PLAYER_ENTERING_WORLD" then
		C_Timer.After(RC.AFTER_LOAD, ClearSoon)
	elseif event == "PLAYER_REGEN_ENABLED" then
		pcall(events.UnregisterEvent, events, "PLAYER_REGEN_ENABLED")
		RC.Clear()
	end
end)
for _, event in ipairs({ "PLAYER_ENTERING_WORLD", "PLAYER_LOGOUT" }) do
	pcall(events.RegisterEvent, events, event)
end
