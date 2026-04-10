"""
Example community detector plugin.
Copy to your external plugins directory and customize.
"""

NAME = "Example Community Detector"
PRIORITY = 10


def detect(window_info, config):
    app_name = str(window_info.get('app_name', '')).lower()
    title = str(window_info.get('title', ''))

    if 'obs' in app_name:
        return {
            'type': 'application',
            'app_name': 'OBS Studio',
            'window_title': title or 'Recording/Streaming'
        }

    return None
