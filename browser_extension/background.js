const api = globalThis.browser || globalThis.chrome;
const ENDPOINT = 'http://127.0.0.1:32191/v1/activity';
const REQUEST_TIMEOUT_MS = 3000;

async function setConnectionBadge(connected) {
  try {
    if (!api?.action?.setBadgeText) return;
    await api.action.setBadgeText({ text: connected ? 'ON' : 'OFF' });
    if (api.action.setBadgeBackgroundColor) {
      await api.action.setBadgeBackgroundColor({
        color: connected ? '#2e7d32' : '#b3261e',
      });
    }
    if (api.action.setTitle) {
      await api.action.setTitle({
        title: connected
          ? 'CYBREX Rich Presence Companion — connected'
          : 'CYBREX Rich Presence Companion — desktop service unavailable',
      });
    }
  } catch (_) {
    // Badge support varies slightly between browsers; never block activity delivery.
  }
}

async function postPayload(payload) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(ENDPOINT, {
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

async function postSnapshot(snapshot, sender) {
  if (!snapshot || typeof snapshot !== 'object') return;
  const tabId = sender?.tab?.id;
  const windowId = sender?.tab?.windowId;
  // Browser APIs normally provide a numeric tab ID. Avoid duplicating a full URL
  // into the local record key on the defensive fallback path.
  const fallbackId = `window:${windowId ?? 'unknown'}`;
  await postPayload({
    ...snapshot,
    tab_id: String(tabId ?? fallbackId),
  });
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
  if (!changeInfo.status && !changeInfo.url && !changeInfo.title) return;
  requestActiveTab(tab.windowId);
});

api.tabs.onRemoved.addListener((tabId) => {
  postPayload({
    version: 1,
    tab_id: String(tabId),
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
