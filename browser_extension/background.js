const api = globalThis.browser || globalThis.chrome;
const DEFAULT_PORT = 32191;
const REQUEST_TIMEOUT_MS = 3000;
const SNAPSHOT_DEDUPE_MS = 1200;
const MAX_RECENT_TABS = 256;
let bridgePort = DEFAULT_PORT;
let lastBadgeState = null;
let lastBadgePort = null;
const recentSnapshots = new Map();

function validPort(value) {
  const port = Number(value);
  return Number.isInteger(port) && port >= 1024 && port <= 65535;
}

async function loadBridgePort() {
  try {
    const stored = await api.storage.local.get('bridgePort');
    if (validPort(stored.bridgePort)) bridgePort = Number(stored.bridgePort);
  } catch (_) {
    bridgePort = DEFAULT_PORT;
  }
}

const portReady = loadBridgePort();

api.storage?.onChanged?.addListener((changes, areaName) => {
  if (areaName !== 'local' || !changes.bridgePort) return;
  const next = changes.bridgePort.newValue;
  bridgePort = validPort(next) ? Number(next) : DEFAULT_PORT;
  lastBadgeState = null;
  lastBadgePort = null;
});

function endpoint(path = '/v1/activity') {
  return `http://127.0.0.1:${bridgePort}${path}`;
}

async function setConnectionBadge(connected) {
  try {
    if (!api?.action?.setBadgeText) return;
    if (lastBadgeState === connected && lastBadgePort === bridgePort) return;
    lastBadgeState = connected;
    lastBadgePort = bridgePort;
    await api.action.setBadgeText({ text: connected ? 'ON' : 'OFF' });
    if (api.action.setBadgeBackgroundColor) {
      await api.action.setBadgeBackgroundColor({
        color: connected ? '#2e7d32' : '#b3261e',
      });
    }
    if (api.action.setTitle) {
      await api.action.setTitle({
        title: connected
          ? `CYBREX Rich Presence Companion — connected on port ${bridgePort}`
          : `CYBREX Rich Presence Companion — desktop service unavailable on port ${bridgePort}`,
      });
    }
  } catch (_) {
    // Badge support varies slightly between browsers; never block activity delivery.
  }
}

async function postPayload(payload) {
  await portReady;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(endpoint(), {
      method: 'POST',
      cache: 'no-store',
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        'X-CYBREX-Companion': '1',
      },
      body: JSON.stringify(payload),
    });
    const connected = response.ok;
    await setConnectionBadge(connected);
    if (!response.ok) {
      console.warn('CYBREX Companion bridge rejected activity:', response.status);
    }
    return connected;
  } catch (_) {
    await setConnectionBadge(false);
    return false;
  } finally {
    clearTimeout(timeoutId);
  }
}

function shouldSuppressSnapshot(tabKey, payload) {
  const now = Date.now();
  const serialized = JSON.stringify(payload);
  const previous = recentSnapshots.get(tabKey);
  recentSnapshots.set(tabKey, {
    serialized,
    at: now,
    browser: String(payload?.browser || ''),
  });

  if (recentSnapshots.size > MAX_RECENT_TABS) {
    const oldest = [...recentSnapshots.entries()]
      .sort((left, right) => left[1].at - right[1].at)
      .slice(0, recentSnapshots.size - MAX_RECENT_TABS);
    for (const [key] of oldest) recentSnapshots.delete(key);
  }

  return Boolean(
    previous &&
    previous.serialized === serialized &&
    now - previous.at < SNAPSHOT_DEDUPE_MS
  );
}

async function postSnapshot(snapshot, sender) {
  if (!snapshot || typeof snapshot !== 'object') return;
  const tabId = sender?.tab?.id;
  const windowId = sender?.tab?.windowId;
  // Browser APIs normally provide a numeric tab ID. Avoid duplicating a full URL
  // into the local record key on the defensive fallback path.
  const fallbackId = `window:${windowId ?? 'unknown'}`;
  const tabKey = String(tabId ?? fallbackId);
  const payload = {
    ...snapshot,
    tab_id: tabKey,
  };
  if (shouldSuppressSnapshot(tabKey, payload)) return;
  await postPayload(payload);
}

api.runtime.onMessage.addListener((message, sender) => {
  if (message?.type !== 'cybrex.activity') return undefined;
  postSnapshot(message.snapshot, sender);
  return undefined;
});

async function requestActiveTab(windowId) {
  try {
    const query = { active: true };
    if (typeof windowId === 'number' && windowId >= 0) query.windowId = windowId;
    else query.lastFocusedWindow = true;
    const tabs = await api.tabs.query(query);
    const tab = tabs?.[0];
    if (!tab?.id) return;
    const snapshot = await api.tabs.sendMessage(tab.id, { type: 'cybrex.snapshot' });
    if (snapshot) await postSnapshot(snapshot, { tab });
  } catch (_) {
    // Restricted pages (browser settings, extension stores, etc.) do not run content scripts.
  }
}

api.tabs.onActivated.addListener((activeInfo) => {
  requestActiveTab(activeInfo.windowId);
});

api.tabs.onUpdated.addListener((_tabId, changeInfo, tab) => {
  if (!tab?.active) return;
  // Do not request the broader `tabs` permission just to inspect URL/title
  // changes. The content script publishes navigation/DOM changes itself; this
  // hook only needs a fresh snapshot once page loading reaches completion.
  if (changeInfo.status !== 'complete') return;
  requestActiveTab(tab.windowId);
});

api.tabs.onRemoved.addListener((tabId) => {
  const tabKey = String(tabId);
  const previous = recentSnapshots.get(tabKey);
  recentSnapshots.delete(tabKey);

  // Tab IDs are browser-local. Include the browser identity learned from the
  // last snapshot so the desktop bridge cannot remove a same-numbered tab that
  // belongs to a different browser. If this tab never produced a snapshot,
  // fail closed and let the short bridge TTL expire any stale state.
  const browser = String(previous?.browser || '').trim();
  if (!browser) return;
  postPayload({
    version: 1,
    browser,
    tab_id: tabKey,
    removed: true,
  });
});

api.windows?.onFocusChanged?.addListener((windowId) => {
  requestActiveTab(windowId);
});

api.runtime.onInstalled?.addListener(() => {
  setConnectionBadge(false);
  requestActiveTab();
});

setConnectionBadge(false);
