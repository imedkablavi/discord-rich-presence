"""
Community plugin detector loader.
"""

import importlib.util
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable

from config import Config

DEFAULT_PLUGIN_PRIORITY = 50


class PluginDetectorManager:
    """Loads and executes community detector plugins."""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.plugins: List[Dict[str, Any]] = []
        self._loaded_dir: Optional[Path] = None
        self.reload()

    def _resolve_plugins_dir(self) -> Path:
        configured = str(self.config.get('plugins.directory', '') or '').strip()
        if configured:
            return Path(configured).expanduser()

        if getattr(self.config, 'config_path', None):
            return self.config.config_path.parent / 'plugins'

        return Path(__file__).resolve().parent / 'plugins'

    def reload(self):
        """Reload plugin modules from plugin directory."""
        plugins_dir = self._resolve_plugins_dir()
        self.plugins = []
        self._loaded_dir = plugins_dir

        if not plugins_dir.exists() or not plugins_dir.is_dir():
            self.logger.info(f"Plugin directory not found: {plugins_dir}")
            return

        enabled = {
            item.lower()
            for x in (self.config.get('plugins.enabled', []) or [])
            for item in [str(x).strip()]
            if item
        }

        for path in sorted(plugins_dir.glob('*.py')):
            if path.name.startswith('_'):
                continue

            plugin_name = path.stem
            if enabled and plugin_name.lower() not in enabled:
                continue

            try:
                spec = importlib.util.spec_from_file_location(f"drp_plugin_{plugin_name}", path)
                if not spec or not spec.loader:
                    continue
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                detector_fn: Optional[Callable[[Dict[str, Any], Config], Optional[Dict[str, Any]]]] = None

                if hasattr(module, 'detect') and callable(module.detect):
                    detector_fn = module.detect
                elif hasattr(module, 'Plugin'):
                    plugin_obj = module.Plugin()
                    if hasattr(plugin_obj, 'detect') and callable(plugin_obj.detect):
                        detector_fn = plugin_obj.detect

                if not detector_fn:
                    self.logger.warning(f"Plugin '{plugin_name}' missing callable detect()")
                    continue

                priority = int(getattr(module, 'PRIORITY', DEFAULT_PLUGIN_PRIORITY))
                display_name = str(getattr(module, 'NAME', plugin_name))

                self.plugins.append({
                    'name': display_name,
                    'id': plugin_name,
                    'detect': detector_fn,
                    'priority': priority,
                })
                self.logger.info(f"Loaded plugin detector: {display_name}")

            except Exception as e:
                self.logger.warning(f"Failed to load plugin '{plugin_name}': {e}")

        self.plugins.sort(key=lambda p: p['priority'], reverse=True)

    def detect(self, window_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Run plugin detectors in priority order and return first match."""
        if not self.config.get('rules.enabled_detectors.plugins', True):
            return None

        for plugin in self.plugins:
            try:
                activity = plugin['detect'](window_info, self.config)
                if activity:
                    if 'type' not in activity:
                        activity['type'] = 'application'
                    return activity
            except Exception as e:
                self.logger.debug(f"Plugin '{plugin['id']}' execution failed: {e}")

        return None
