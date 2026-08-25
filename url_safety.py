"""Shared URL safety rules for links that can leave the local machine."""

from __future__ import annotations

import ipaddress
from typing import Any
from urllib.parse import urlsplit


_BLOCKED_HOSTS = {'localhost', 'localhost.localdomain'}
_BLOCKED_SUFFIXES = ('.localhost', '.local', '.internal')


def contains_controls(text: str) -> bool:
    return any(ord(char) < 32 or ord(char) == 127 for char in text)


def is_public_hostname(hostname: str) -> bool:
    """Return True for a syntactically public host without doing DNS resolution.

    Literal private/loopback/link-local/reserved IP addresses and common local
    DNS suffixes are rejected. Hostnames are intentionally not DNS-resolved here:
    validation must stay deterministic and must not turn display-data handling
    into an SSRF/DNS side effect.
    """
    host = str(hostname or '').strip().lower().rstrip('.')
    if not host or '%' in host:
        return False
    if host in _BLOCKED_HOSTS or host.endswith(_BLOCKED_SUFFIXES):
        return False

    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        # Rich Presence links are meant to be public. Reject bare intranet names
        # and malformed IDNs while allowing normal DNS names.
        if '.' not in host:
            return False
        try:
            ascii_host = host.encode('idna').decode('ascii')
        except (UnicodeError, ValueError):
            return False
        labels = ascii_host.split('.')
        return all(
            label
            and len(label) <= 63
            and not label.startswith('-')
            and not label.endswith('-')
            for label in labels
        )

    return bool(address.is_global)


def public_https_url(value: Any, limit: int) -> str | None:
    """Return a safe public HTTPS URL or None.

    Discord buttons, activity links, and external artwork are visible outside the
    application. They must never publish credentials or local/private endpoints.
    """
    text = str(value or '').strip().strip('`')
    if not text or len(text) > limit or contains_controls(text):
        return None
    try:
        parsed = urlsplit(text)
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError:
        return None
    if parsed.scheme.lower() != 'https' or not hostname:
        return None
    if parsed.username is not None or parsed.password is not None:
        return None
    if not is_public_hostname(hostname):
        return None
    return text
