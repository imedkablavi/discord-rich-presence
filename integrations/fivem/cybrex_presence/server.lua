local function safeJoinUrl()
    local value = tostring(GetConvar('cybrex_join_url', '') or '')
    if string.match(value, '^https://cfx%.re/join/[A-Za-z0-9_-]+/?$') then
        return value
    end
    return ''
end

local function sendSnapshot(target)
    if not target or target <= 0 then
        return
    end

    local players = GetPlayers()
    local maxPlayers = GetConvarInt('sv_maxclients', 0)
    local serverName = tostring(GetConvar('sv_hostname', 'FiveM') or 'FiveM')

    TriggerClientEvent('cybrex_presence:snapshot', target, {
        server_name = string.sub(serverName, 1, 128),
        player_count = #players,
        max_players = maxPlayers,
        join_url = safeJoinUrl()
    })
end

RegisterNetEvent('cybrex_presence:request', function()
    local playerSource = source
    sendSnapshot(playerSource)
end)
