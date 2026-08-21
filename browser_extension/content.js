(() => {
  const api = globalThis.browser || globalThis.chrome;
  const SERVICE_MAP = [
    [/^(www\.)?youtube\.com$/i, 'YouTube'],
    [/^music\.youtube\.com$/i, 'YouTube Music'],
    [/^(www\.)?netflix\.com$/i, 'Netflix'],
    [/^(www\.)?twitch\.tv$/i, 'Twitch'],
    [/^open\.spotify\.com$/i, 'Spotify'],
    [/^(www\.)?soundcloud\.com$/i, 'SoundCloud'],
    [/^(www\.)?disneyplus\.com$/i, 'Disney+'],
    [/^(www\.)?hulu\.com$/i, 'Hulu'],
    [/^(www\.)?primevideo\.com$/i, 'Prime Video'],
    [/^(www\.)?github\.com$/i, 'GitHub'],
    [/^(www\.)?reddit\.com$/i, 'Reddit'],
    [/^(www\.)?(x|twitter)\.com$/i, 'X'],
    [/^chatgpt\.com$/i, 'ChatGPT'],
  ];

  let lastSent = '';
  let lastSentAt = 0;

  function detectBrowser() {
    const ua = navigator.userAgent || '';
    if (navigator.brave) return 'Brave';
    if (/Edg\//.test(ua)) return 'Edge';
    if (/OPR\//.test(ua)) return 'Opera';
    if (/Vivaldi\//.test(ua)) return 'Vivaldi';
    if (/Firefox\//.test(ua)) return 'Firefox';
    if (/Chromium\//.test(ua)) return 'Chromium';
    if (/Chrome\//.test(ua)) return 'Chrome';
    return 'Browser';
  }

  function detectService() {
    const host = location.hostname.toLowerCase();
    for (const [pattern, name] of SERVICE_MAP) {
      if (pattern.test(host)) return name;
    }
    return '';
  }

  function bestMediaElement() {
    const media = [...document.querySelectorAll('video, audio')];
    return media.find((element) => !element.paused && !element.ended) || media[0] || null;
  }

  function text(selector) {
    const element = document.querySelector(selector);
    return (element?.textContent || '').trim();
  }

  function mediaMetadata(service, element) {
    if (!element) {
      return { playing: false, position: 0, duration: 0, title: '', artist: '' };
    }

    let title = document.title || '';
    let artist = '';
    if (service === 'YouTube' || service === 'YouTube Music') {
      title = text('h1.ytd-watch-metadata yt-formatted-string') ||
        text('h1.title yt-formatted-string') ||
        text('yt-formatted-string.ytd-watch-metadata') ||
        title.replace(/\s*-\s*YouTube\s*$/i, '');
      artist = text('ytd-channel-name a') || text('#owner-name a') || text('.byline a');
    } else if (service === 'Twitch') {
      title = text('[data-a-target="stream-title"]') || title;
      artist = text('[data-a-target="stream-game-link"]') || '';
    }

    const currentTime = Number.isFinite(element.currentTime) ? element.currentTime : 0;
    const duration = Number.isFinite(element.duration) ? element.duration : 0;
    return {
      playing: !element.paused && !element.ended,
      position: Math.max(0, currentTime || 0),
      duration: Math.max(0, duration || 0),
      title: String(title || '').slice(0, 300),
      artist: String(artist || '').slice(0, 200),
    };
  }

  function buildSnapshot() {
    const service = detectService();
    const element = bestMediaElement();
    return {
      version: 1,
      browser: detectBrowser(),
      url: location.href,
      title: document.title || '',
      service,
      private: Boolean(api?.extension?.inIncognitoContext),
      focused: document.hasFocus(),
      visible: document.visibilityState === 'visible',
      media: mediaMetadata(service, element),
    };
  }

  function publish(force = false) {
    if (!api?.runtime?.sendMessage) return;
    const snapshot = buildSnapshot();
    if (!snapshot.visible && !snapshot.media.playing) return;
    const serialized = JSON.stringify(snapshot);
    const now = Date.now();
    if (!force && serialized === lastSent && now - lastSentAt < 5000) return;
    if (!force && now - lastSentAt < 1500) return;
    lastSent = serialized;
    lastSentAt = now;
    try {
      const result = api.runtime.sendMessage({ type: 'cybrex.activity', snapshot });
      if (result && typeof result.catch === 'function') result.catch(() => {});
    } catch (_) {
      // Extension may be reloading; the next event will retry.
    }
  }

  api?.runtime?.onMessage?.addListener((message, _sender, sendResponse) => {
    if (message?.type !== 'cybrex.snapshot') return undefined;
    sendResponse(buildSnapshot());
    return true;
  });

  for (const eventName of ['play', 'pause', 'seeking', 'seeked', 'ended']) {
    document.addEventListener(eventName, () => publish(true), true);
  }
  document.addEventListener('visibilitychange', () => publish(true));
  window.addEventListener('focus', () => publish(true));
  window.addEventListener('blur', () => publish(true));
  window.addEventListener('popstate', () => publish(true));
  window.addEventListener('hashchange', () => publish(true));

  const observer = new MutationObserver(() => publish(false));
  observer.observe(document.documentElement, { subtree: true, childList: true });

  setInterval(() => publish(false), 2000);
  publish(true);
})();
