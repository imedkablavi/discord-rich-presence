local RESOURCE = GetCurrentResourceName()

RegisterNetEvent('cybrex_presence:snapshot', function(payload)
    if type(payload) ~= 'table' then
        return
    end

    local port = GetConvarInt('cybrex_presence_port', 32193)
    if port < 1024 or port > 65535 then
        port = 32193
    end

    SendNUIMessage({
        type = 'cybrex_presence',
        port = port,
        payload = {
            server_name = tostring(payload.server_name or ''),
            player_count = tonumber(payload.player_count or 0) or 0,
            max_players = tonumber(payload.max_players or 0) or 0,
            join_url = tostring(payload.join_url or '')
        }
    })
end)

CreateThread(function()
    while true do
        TriggerServerEvent('cybrex_presence:request')
        Wait(5000)
    end
end)

AddEventHandler('onClientResourceStart', function(resourceName)
    if resourceName ~= RESOURCE then
        return
    end
    TriggerServerEvent('cybrex_presence:request')
end)
