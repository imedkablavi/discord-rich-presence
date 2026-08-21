import asyncio

from config import Config
from detectors import media_windows
from detectors.media_windows import WindowsMediaDetector


def test_windows_media_detection_uses_managed_asyncio_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setattr(media_windows, 'WINDOWS_MEDIA_AVAILABLE', True)
    detector = WindowsMediaDetector(Config(tmp_path / 'config.yaml'))

    async def fake_detect():
        await asyncio.sleep(0)
        return {'type': 'media', 'player': 'Test', 'is_playing': True}

    monkeypatch.setattr(detector, '_detect_async', fake_detect)
    monkeypatch.setattr(
        media_windows.asyncio,
        'new_event_loop',
        lambda: (_ for _ in ()).throw(AssertionError('manual event loop must not be created')),
    )

    assert detector.detect({}) == {
        'type': 'media', 'player': 'Test', 'is_playing': True,
    }


def test_windows_media_exception_does_not_escape_detector(tmp_path, monkeypatch):
    monkeypatch.setattr(media_windows, 'WINDOWS_MEDIA_AVAILABLE', True)
    detector = WindowsMediaDetector(Config(tmp_path / 'config.yaml'))

    async def failing_detect():
        await asyncio.sleep(0)
        raise RuntimeError('simulated WinRT failure')

    monkeypatch.setattr(detector, '_detect_async', failing_detect)
    assert detector.detect({}) is None
