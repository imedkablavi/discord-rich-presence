# Social web presence

CYBREX Presence can recognize major social and messaging web applications through the existing Browser Companion while keeping a stricter privacy contract than ordinary browser pages.

## Supported services

- WhatsApp Web
- Facebook
- Messenger
- Instagram
- LinkedIn
- Threads
- TikTok
- Telegram Web
- Snapchat Web
- Discord Web
- Pinterest
- Bluesky
- X
- Reddit

The built-in service list is intentionally domain-based. Custom/self-hosted services can still be mapped with `browser_companion.domain_services`.

## What Discord receives

For social/messaging services the desktop detector publishes only generic state such as:

```text
Using Instagram
Instagram · Firefox
```

or:

```text
Using WhatsApp
WhatsApp · Chrome
```

The optional Open button points to the public service homepage, not the current private page.

## What is deliberately discarded

Before the Presence payload is built, CYBREX discards:

- tab/page title;
- conversation or group name;
- contact/display name;
- username/profile handle taken from the page title;
- direct-message thread URLs;
- profile/post/video/status identifiers;
- query strings and fragments from the current social page;
- social-page media metadata.

This protection applies even if `privacy.browser_url_mode` is configured as `path` or `full` for ordinary browser pages.

The Browser Companion may briefly hold the active tab title and URL in local memory because that is how it identifies the focused page. Records expire under the normal Browser Companion TTL and are not sent to a CYBREX cloud service. The social detector reduces the data to the generic service identity before Presence building.

## Private browsing

Private/Incognito/InPrivate behavior is unchanged. A private browser window produces generic private-browsing Presence and does not expose the service or URL.

## Permissions

Social support does not add browser permissions. The Browser Companion keeps its existing model:

- content scripts on normal HTTP/HTTPS pages;
- no `tabs` permission;
- no `file://` access;
- local bridge access only at `127.0.0.1`.

## Domain matching

Known services are matched structurally against the parsed URL hostname/path. A social URL appearing only inside another site's query string does not classify that unrelated site as the social service.

For example, this must remain an unknown site:

```text
https://example.com/redirect?next=https://www.instagram.com/direct/t/123
```

## Privacy regression tests

`tests/test_social_presence.py` verifies:

- known social domains and web-app paths;
- query-string false-positive resistance;
- deep-link removal;
- page-title removal;
- media-metadata removal;
- generic homepage-only buttons/URLs;
- window-title fallback without Browser Companion.
