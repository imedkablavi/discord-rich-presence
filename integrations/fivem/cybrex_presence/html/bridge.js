(() => {
  'use strict';

  const MIN_PORT = 1024;
  const MAX_PORT = 65535;

  function safePort(value) {
    const port = Number.parseInt(String(value ?? ''), 10);
    return Number.isInteger(port) && port >= MIN_PORT && port <= MAX_PORT ? port : 32193;
  }

  function safePayload(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
    return {
      server_name: String(value.server_name ?? '').slice(0, 128),
      player_count: Number.isFinite(Number(value.player_count)) ? Number(value.player_count) : 0,
      max_players: Number.isFinite(Number(value.max_players)) ? Number(value.max_players) : 0,
      join_url: String(value.join_url ?? '').slice(0, 160),
    };
  }

  window.addEventListener('message', (event) => {
    const message = event?.data;
    if (!message || message.type !== 'cybrex_presence') return;
    const payload = safePayload(message.payload);
    if (!payload) return;

    const port = safePort(message.port);
    fetch(`http://127.0.0.1:${port}/presence`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload),
      cache: 'no-store',
      credentials: 'omit',
      referrerPolicy: 'no-referrer',
    }).catch(() => {
      // CYBREX is optional. A server resource must never break gameplay when the
      // desktop companion is not installed or not currently running.
    });
  });
})();
