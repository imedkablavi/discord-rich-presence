#!/usr/bin/env python3
"""Real-device smoke test for the optional Discord Social SDK transport."""

from __future__ import annotations

import argparse
import time

from config import BUILTIN_DISCORD_APPLICATION_ID
from social_sdk_transport import SocialSDKError, SocialSDKPresence, discover_social_sdk_helper


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Publish a short Social SDK Rich Presence to verify dynamic activity names.'
    )
    parser.add_argument('--name', default='Firefox', help='Top-line activity name to test')
    parser.add_argument('--seconds', type=int, default=20, help='How long to keep the test presence')
    args = parser.parse_args()

    helper = discover_social_sdk_helper()
    if helper is None:
        print('Social SDK helper not found.')
        print('Build native/discord_social_sdk_bridge first or set CYBREX_DISCORD_SOCIAL_SDK_HELPER.')
        return 2

    name = str(args.name or '').strip()
    if len(name) < 2:
        print('Test name must contain at least two characters.')
        return 2
    seconds = max(3, min(int(args.seconds), 300))

    presence = SocialSDKPresence(BUILTIN_DISCORD_APPLICATION_ID, helper_path=helper)
    try:
        presence.connect()
        presence.update(
            activity_type=0,
            details='CYBREX Social SDK transport test',
            state='Dynamic activity name validation',
            large_image='https://www.google.com/s2/favicons?domain=discord.com&sz=256',
            large_text=name,
            start=int(time.time() * 1000),
        )
        print(f'Published Social SDK test as {name!r} for {seconds} seconds.')
        print('Check the top line of your Discord activity card now.')
        time.sleep(seconds)
        presence.clear()
        print('Test presence cleared.')
        return 0
    except (SocialSDKError, OSError, ValueError) as exc:
        print(f'Social SDK test failed: {exc}')
        return 1
    finally:
        presence.close()


if __name__ == '__main__':
    raise SystemExit(main())
