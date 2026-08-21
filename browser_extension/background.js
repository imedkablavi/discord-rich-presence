const api = globalThis.browser || globalThis.chrome;
const ENDPOINT = 'http://127.0.0.1:32191/v1/activity';

async function postPayload(payload) {
  try {
    await fetch(ENDPOINT, {
      method: 'POST',
      cache: 'no-store',
      headers: {
        'Content-Type': 'application/json',
        'X-CYBREX-Companion': '1',
      },
      body: JSON.stringify(payload),
    });
  } catch (_) {
    // Desktop service is optional and may not be running yet.
  }
}

async function postSnapshot(snapshot, sender) {
  if (!snapshot || typeof snapshot !== 'object') return;
  const tabId = sender?.tab?.id;
  const windowId = sender?.tab?.windowId;
  await postPayload({
    ...snapshot,
    tab_id: String(tabId ?? `${windowId ?? 'window'}:${snapshot.url || 'unknown'}`),
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
  requestActiveTab();
});
