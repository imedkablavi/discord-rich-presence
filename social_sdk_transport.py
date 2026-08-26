"""Optional Discord Social SDK Rich Presence transport.

The Social SDK is native. This adapter talks to a small CYBREX helper over
private stdin/stdout pipes. It does not open a network listener and does not
handle Discord user OAuth or account tokens.
"""

from __future__ import annotations

import os
import queue
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Callable, Optional

from social_sdk_protocol import decode_message, encode_command, encode_update


class SocialSDKError(RuntimeError):
    pass


_HELPER_NAME = (
    "cybrex-discord-social-sdk.exe"
    if sys.platform == "win32"
    else "cybrex-discord-social-sdk"
)


def discover_social_sdk_helper() -> Optional[Path]:
    """Find a locally installed helper without downloading or executing it."""
    explicit = os.environ.get("CYBREX_DISCORD_SOCIAL_SDK_HELPER", "").strip()
    if explicit:
        candidate = Path(explicit).expanduser()
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            pass

    executable_dir = Path(sys.executable).resolve(strict=False).parent
    source_dir = Path(__file__).resolve(strict=False).parent
    candidates = [
        executable_dir / _HELPER_NAME,
        source_dir / _HELPER_NAME,
        source_dir / "bin" / _HELPER_NAME,
        source_dir / "native" / "discord_social_sdk_bridge" / "build" / _HELPER_NAME,
        source_dir / "native" / "discord_social_sdk_bridge" / "build" / "Release" / _HELPER_NAME,
    ]
    on_path = shutil.which(_HELPER_NAME)
    if on_path:
        candidates.append(Path(on_path))

    seen: set[str] = set()
    for candidate in candidates:
        key = os.path.normcase(str(candidate))
        if key in seen:
            continue
        seen.add(key)
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


def social_sdk_available() -> bool:
    return discover_social_sdk_helper() is not None


class SocialSDKPresence:
    """Small pypresence-like adapter backed by the optional native helper."""

    def __init__(
        self,
        client_id: str | int,
        helper_path: Optional[Path] = None,
        *,
        response_timeout: float = 6.0,
        popen_factory: Callable[..., subprocess.Popen[str]] = subprocess.Popen,
    ) -> None:
        raw_id = str(client_id or "").strip()
        if not raw_id.isdigit() or int(raw_id) <= 0:
            raise SocialSDKError("invalid Discord application ID")
        self.application_id = raw_id
        self.helper_path = helper_path or discover_social_sdk_helper()
        self.response_timeout = max(1.0, min(float(response_timeout), 30.0))
        self._popen_factory = popen_factory
        self._process: Optional[subprocess.Popen[str]] = None
        self._responses: queue.Queue[str | None] = queue.Queue(maxsize=16)
        self._reader_thread: Optional[threading.Thread] = None
        self._command_lock = threading.Lock()
        self._closed = False

    @property
    def helper_name(self) -> str:
        return self.helper_path.name if self.helper_path else "unavailable"

    def connect(self) -> None:
        if self._closed:
            raise SocialSDKError("Social SDK transport is already closed")
        if self._process is not None and self._process.poll() is None:
            return
        if self.helper_path is None or not self.helper_path.is_file():
            raise SocialSDKError("Discord Social SDK helper is not installed")

        kwargs: dict[str, Any] = {
            "stdin": subprocess.PIPE,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.DEVNULL,
            "text": True,
            "encoding": "utf-8",
            "errors": "strict",
            "bufsize": 1,
        }
        if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW"):
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        try:
            process = self._popen_factory([str(self.helper_path)], **kwargs)
        except (OSError, ValueError) as exc:
            raise SocialSDKError(
                f"could not start Discord Social SDK helper: {exc}"
            ) from exc

        self._process = process
        self._responses = queue.Queue(maxsize=16)
        self._reader_thread = threading.Thread(
            target=self._read_responses,
            name="cybrex-social-sdk-reader",
            daemon=True,
        )
        self._reader_thread.start()
        try:
            self._command(encode_command("PING"))
            self._command(
                encode_command("SET_APP", {"application_id": self.application_id})
            )
        except Exception:
            self._terminate_process()
            raise

    def _read_responses(self) -> None:
        process = self._process
        if process is None or process.stdout is None:
            return
        try:
            for line in process.stdout:
                try:
                    self._responses.put(line, timeout=0.5)
                except queue.Full:
                    break
        except (OSError, UnicodeError):
            pass
        finally:
            try:
                self._responses.put_nowait(None)
            except queue.Full:
                pass

    def _command(self, line: str) -> dict[str, str]:
        with self._command_lock:
            process = self._process
            if process is None or process.poll() is not None or process.stdin is None:
                raise SocialSDKError("Discord Social SDK helper is not running")
            try:
                process.stdin.write(line)
                process.stdin.flush()
            except (BrokenPipeError, OSError, UnicodeError) as exc:
                raise SocialSDKError("Discord Social SDK helper pipe closed") from exc

            try:
                response = self._responses.get(timeout=self.response_timeout)
            except queue.Empty as exc:
                raise SocialSDKError("Discord Social SDK helper timed out") from exc
            if response is None:
                raise SocialSDKError("Discord Social SDK helper exited unexpectedly")

            try:
                op, fields = decode_message(response)
            except (TypeError, ValueError) as exc:
                raise SocialSDKError(
                    "Discord Social SDK helper returned an invalid response"
                ) from exc
            if op == "OK":
                return fields
            if op == "ERR":
                code = str(fields.get("code") or "unknown_error")[:80]
                raise SocialSDKError(
                    f"Discord Social SDK helper rejected command: {code}"
                )
            raise SocialSDKError(
                f"unexpected Discord Social SDK helper response: {op[:32]}"
            )

    def update(self, *, name: str | None = None, **payload: Any) -> None:
        if self._process is None or self._process.poll() is not None:
            self.connect()
        self._command(encode_update(payload, name=name))

    def clear(self) -> None:
        if self._process is None or self._process.poll() is not None:
            return
        self._command(encode_command("CLEAR"))

    def _terminate_process(self) -> None:
        process = self._process
        self._process = None
        if process is None:
            return
        try:
            if process.stdin:
                process.stdin.close()
        except OSError:
            pass
        if process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=2.0)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    process.kill()
                    process.wait(timeout=1.0)
                except (OSError, subprocess.TimeoutExpired):
                    pass
        try:
            if process.stdout:
                process.stdout.close()
        except OSError:
            pass

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        process = self._process
        if process is not None and process.poll() is None:
            try:
                self._command(encode_command("QUIT"))
            except SocialSDKError:
                pass
        self._terminate_process()
        reader = self._reader_thread
        self._reader_thread = None
        if reader is not None and reader.is_alive():
            reader.join(timeout=1.0)
