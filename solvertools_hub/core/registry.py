"""
registry.py - Plugin Registry and auto-discovery system for solvertools_hub.
Allows plugins to be loaded explicitly or auto-discovered dynamically,
filtered through solvertools_hub/plugins_config.json to hide drafts/WIP plugins.
"""

import importlib
import inspect
import json
from pathlib import Path
import pkgutil
from typing import Any, Dict, List, Optional, Type, Union

from loguru import logger

from .base_plugin import BasePuzzlePlugin


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "plugins_config.json"


class PluginRegistry:
    """Central repository of registered puzzle plugins."""

    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        self._plugins: Dict[str, BasePuzzlePlugin] = {}
        self._disabled_plugins: Dict[str, BasePuzzlePlugin] = {}
        self._config_path: Path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self._config: Dict[str, Any] = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Loads plugin activation configuration from JSON file."""
        if self._config_path.is_file():
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.debug(f"Loaded plugin configuration from {self._config_path}")
                    return data
            except Exception as e:
                logger.warning(f"Failed to parse plugin config at {self._config_path}: {e}")
        return {"plugins": {}, "default_enabled": True}

    def save_config(self, path: Optional[Union[str, Path]] = None) -> None:
        """Saves current config to JSON file."""
        save_path = Path(path) if path else self._config_path
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2)
            logger.info(f"Saved plugin configuration to {save_path}")
        except Exception as e:
            logger.error(f"Failed to write plugin config to {save_path}: {e}")

    def get_config(self) -> Dict[str, Any]:
        """Returns a copy of the active configuration dictionary."""
        return dict(self._config)

    def is_plugin_enabled(self, name: str, is_wip: bool = False) -> bool:
        """
        Determines if a plugin should be activated based on config and WIP flag.
        1. Exact match in config["plugins"][name]["enabled"] takes precedence.
        2. Flexible prefix / substring matching (e.g. "Sliding Tile" -> "Sliding Tile (N-Puzzle)").
        3. If not specified and is_wip is True, defaults to False.
        4. Otherwise defaults to config["default_enabled"].
        """
        plugins_cfg = self._config.get("plugins", {})
        # 1. Exact match
        if name in plugins_cfg and isinstance(plugins_cfg[name], dict):
            entry = plugins_cfg[name]
            if "enabled" in entry:
                return bool(entry["enabled"])

        # 2. Case-insensitive / prefix match
        name_lower = name.lower()
        for cfg_name, entry in plugins_cfg.items():
            if isinstance(entry, dict) and "enabled" in entry:
                cfg_lower = cfg_name.lower()
                if cfg_lower == name_lower or cfg_lower in name_lower or name_lower.startswith(cfg_lower):
                    return bool(entry["enabled"])

        # 3. Code-level WIP flag
        if is_wip:
            return False

        return bool(self._config.get("default_enabled", True))

    def set_plugin_enabled(self, name: str, enabled: bool) -> None:
        """Toggles the enabled status of a plugin in the in-memory config."""
        plugins_cfg = self._config.setdefault("plugins", {})
        entry = plugins_cfg.setdefault(name, {})
        entry["enabled"] = enabled

    def register(self, plugin: BasePuzzlePlugin) -> None:
        """Registers an active puzzle plugin instance."""
        if not isinstance(plugin, BasePuzzlePlugin):
            raise TypeError(f"Expected BasePuzzlePlugin, got {type(plugin)}")
        if plugin.name in self._plugins:
            logger.warning(f"Plugin '{plugin.name}' is already registered. Overwriting.")
        self._plugins[plugin.name] = plugin
        logger.info(f"Registered plugin: {plugin.name} [{plugin.category}]")

    def register_all(self, plugins: List[BasePuzzlePlugin]) -> None:
        """Registers a list of puzzle plugin instances."""
        for p in plugins:
            self.register(p)

    def get_plugin(self, name: str) -> Optional[BasePuzzlePlugin]:
        """Retrieves a registered plugin by name."""
        return self._plugins.get(name)

    def list_plugins(self) -> List[BasePuzzlePlugin]:
        """Returns all registered plugins in order."""
        return list(self._plugins.values())

    def list_disabled_plugins(self) -> List[BasePuzzlePlugin]:
        """Returns all discovered plugins that were excluded by config."""
        return list(self._disabled_plugins.values())

    def categories(self) -> List[str]:
        """Returns distinct sorted categories of active plugins."""
        return sorted(list({p.category for p in self._plugins.values()}))

    def auto_discover(
        self,
        package_name: str = "solvertools_hub.plugins",
        include_disabled: bool = False,
    ) -> None:
        """
        Discovers all BasePuzzlePlugin subclasses in the given package and
        registers active ones based on plugins_config.json.
        """
        try:
            package = importlib.import_module(package_name)
        except ImportError as exc:
            logger.error(f"Cannot import plugin package '{package_name}': {exc}")
            return

        if not hasattr(package, "__path__"):
            return

        # Reload config in case it changed on disk
        self._config = self._load_config()

        for _, modname, ispkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
            try:
                module = importlib.import_module(modname)
                for _, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BasePuzzlePlugin) and obj is not BasePuzzlePlugin:
                        try:
                            inst = obj()
                            plugin_name = inst.name
                            is_wip = getattr(inst, "is_wip", False)
                            enabled = self.is_plugin_enabled(plugin_name, is_wip=is_wip)

                            if enabled or include_disabled:
                                self.register(inst)
                            else:
                                self._disabled_plugins[plugin_name] = inst
                                logger.debug(
                                    f"Curtain: Skipping disabled/WIP plugin '{plugin_name}'"
                                )
                        except Exception as e:
                            logger.error(f"Failed to instantiate plugin class {obj.__name__}: {e}")
            except Exception as exc:
                logger.debug(f"Skipping module {modname} during auto-discovery: {exc}")
