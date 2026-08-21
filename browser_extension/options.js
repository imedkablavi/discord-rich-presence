const api = globalThis.browser || globalThis.chrome;
const DEFAULT_PORT = 32191;
const REQUEST_TIMEOUT_MS = 3000;

function validPort(value) {
  const port = Number(value);
  return Number.isInteger(port) && port >= 1024 && port <= 65535;
}

function setStatus(message, ok = true) {
  const status = document.getElementById('status');
  status.textContent = message;
  status.dataset.ok = ok ? 'true' : 'false';
}

async function load() {
  try {
    const stored = await api.storage.local.get('bridgePort');
    const port = validPort(stored.bridgePort) ? Number(stored.bridgePort) : DEFAULT_PORT;
    document.getElementById('port').value = String(port);
  } catch (_) {
    document.getElementById('port').value = String(DEFAULT_PORT);
    setStatus('Could not read extension settings; using the default port.', false);
  }
}

async function save() {
  const value = Number(document.getElementById('port').value);
  if (!validPort(value)) {
    setStatus('Port must be an integer between 1024 and 65535.', false);
    return false;
  }
  try {
    await api.storage.local.set({ bridgePort: value });
    setStatus(`Saved port ${value}.`);
    return true;
  } catch (_) {
    setStatus('Could not save the port.', false);
    return false;
  }
}

async function testConnection() {
  const value = Number(document.getElementById('port').value);
  if (!validPort(value)) {
    setStatus('Port must be an integer between 1024 and 65535.', false);
    return;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(`http://127.0.0.1:${value}/v1/health`, {
      cache: 'no-store',
      signal: controller.signal,
    });
    if (!response.ok) {
      setStatus(`Desktop bridge returned HTTP ${response.status}.`, false);
      return;
    }
    const data = await response.json();
    if (!data?.ok) {
      setStatus('Desktop bridge returned an unexpected response.', false);
      return;
    }
    setStatus(`Connected to the desktop bridge on port ${value}.`);
  } catch (_) {
    setStatus(`Could not reach the desktop bridge on port ${value}.`, false);
  } finally {
    clearTimeout(timeoutId);
  }
}

document.getElementById('save').addEventListener('click', save);
document.getElementById('test').addEventListener('click', testConnection);
load();
