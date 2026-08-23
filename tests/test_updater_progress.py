import hashlib

import updater
from updater import ReleaseAsset, download_verified_asset


class Response:
    status = 200

    def __init__(self, payload: bytes):
        self.payload = payload
        self.sent = False

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def geturl(self):
        return 'https://example.invalid/app.bin'

    def read(self, _size=-1):
        if self.sent:
            return b''
        self.sent = True
        return self.payload


def test_verified_download_reports_real_byte_progress(monkeypatch, tmp_path):
    payload = b'new-binary-data'
    asset = ReleaseAsset(
        name='app.bin',
        url='https://example.invalid/app.bin',
        sha256=hashlib.sha256(payload).hexdigest(),
        size=len(payload),
        platform='linux',
        arch='x86_64',
    )
    monkeypatch.setattr(
        updater.urllib.request,
        'urlopen',
        lambda _request, timeout=30.0: Response(payload),
    )
    progress = []
    target = tmp_path / 'app.bin'

    result = download_verified_asset(
        asset,
        target,
        progress=lambda done, total: progress.append((done, total)),
    )

    assert result == target
    assert target.read_bytes() == payload
    assert progress[0] == (0, len(payload))
    assert progress[-1] == (len(payload), len(payload))
