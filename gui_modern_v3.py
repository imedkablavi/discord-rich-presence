"""Resource-aware CYBREX control panel.

Builds on the polished Arabic-safe UI while ensuring periodic integration
probes do not create a fresh OS thread every few seconds for the lifetime of
the window.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from config import Config
from gui_modern_v2 import ModernControlPanel as PolishedControlPanel


class ModernControlPanel(PolishedControlPanel):
    """Polished UI with bounded long-running probe resources."""

    INTEGRATION_POLL_MS = 10_000

    def __init__(self, config: Config):
        self._probe_executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="cybrex-gui-probe",
        )
        self._probe_future = None
        self._closing = False
        super().__init__(config)

    def _poll_integrations(self):
        if self._closing:
            return

        future = self._probe_future
        if future is not None and future.done():
            self._probe_future = None
            try:
                browser_ok, cs2_ok, cs2_data = future.result()
            except Exception:
                browser_ok, cs2_ok, cs2_data = False, False, None

            self.browser_value.configure(
                text="Connected" if browser_ok else "Not connected",
                text_color=self.SUCCESS if browser_ok else self.MUTED,
            )
            self.browser_status_label.configure(
                text="Status: connected" if browser_ok else "Status: not connected",
                text_color=self.SUCCESS if browser_ok else self.MUTED,
            )
            if cs2_ok:
                connected = bool((cs2_data or {}).get("connected", False))
                label = "Match data active" if connected else "Listener ready"
                color = self.SUCCESS if connected else self.PRIMARY
            else:
                label = "Not connected"
                color = self.MUTED
            self.cs2_value.configure(text=label, text_color=color)
            self.cs2_status_label.configure(text=f"Status: {label.lower()}", text_color=color)

        if self._probe_future is None:
            browser_port = self._safe_port(
                self.config.get("browser_companion.port", 32191), 32191
            )
            cs2_port = self._safe_port(self.config.get("cs2_gsi.port", 32192), 32192)

            def collect():
                browser_ok, _, _ = self._probe_json(
                    f"http://127.0.0.1:{browser_port}/v1/health", 0.6
                )
                cs2_ok, cs2_data, _ = self._probe_json(
                    f"http://127.0.0.1:{cs2_port}/v1/status", 0.6
                )
                return browser_ok, cs2_ok, cs2_data

            self._probe_future = self._probe_executor.submit(collect)

        self.after(self.INTEGRATION_POLL_MS, self._poll_integrations)

    def destroy(self):
        if self._closing:
            return
        self._closing = True
        try:
            self._probe_executor.shutdown(wait=False, cancel_futures=True)
        finally:
            super().destroy()


if __name__ == "__main__":
    app = ModernControlPanel(Config())
    app.mainloop()
