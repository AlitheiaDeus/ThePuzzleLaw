"""
registry.py - Plugin Registry and auto-discovery system for solvertools_hub.
Allows plugins to be loaded explicitly or auto-discovered dynamically.
"""

import importlib
import inspect
import pkgutil
from typing import Dict, List, Optional, Type

from loguru import logger

from .base_plugin import BasePuzzlePlugin


class PluginRegistry:
    """Central repository of registered puzzle plugins."""

    def __init__(self):
        self._plugins: Dict[str, BasePuzzlePlugin] = {}

    def register(self, plugin: BasePuzzlePlugin) -> None:
        """Registers a puzzle plugin instance."""
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

    def categories(self) -> List[str]:
        """Returns distinct sorted categories."""
        return sorted(list({p.category for p in self._plugins.values()}))

    def auto_discover(self, package_name: str = "solvertools_hub.plugins") -> None:
        """
        Discovers and registers all BasePuzzlePlugin subclasses in the given package.
        """
        try:
            package = importlib.import_module(package_name)
        except ImportError as exc:
            logger.error(f"Cannot import plugin package '{package_name}': {exc}")
            return

        if not hasattr(package, "__path__"):
            return

        for _, modname, ispkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
            try:
                module = importlib.import_module(modname)
                for _, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BasePuzzlePlugin) and obj is not BasePuzzlePlugin:
                        # Instantiate and register
                        try:
                            inst = obj()
                            self.register(inst)
                        except Exception as e:
                            logger.error(f"Failed to instantiate plugin class {obj.__name__}: {e}")
            except Exception as exc:
                logger.debug(f"Skipping module {modname} during auto-discovery: {exc}")
