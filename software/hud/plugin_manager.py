#!/usr/bin/env python3

import importlib
import importlib.util
import inspect
import sys
import time
from pathlib import Path
from typing import List, Dict, Type, Optional, Any
import numpy as np

from .plugin_base import HUDPlugin, HUDContext, PluginConfig, PluginMetadata


class PluginManager:
    def __init__(self, context: HUDContext, plugin_dir: str = "hud/plugins"):
        self.context = context
        self.plugin_dir = Path(plugin_dir)
        self.plugins: List[HUDPlugin] = []
        self.plugin_classes: Dict[str, Type[HUDPlugin]] = {}
        self.plugin_modules: Dict[str, Any] = {}
        self.plugin_file_times: Dict[str, float] = {}
        self.last_update_time = time.time()

    def _get_metadata(self, plugin_class: Type[HUDPlugin]) -> PluginMetadata:
        """Get metadata from plugin class without instantiation."""
        if not hasattr(plugin_class, 'METADATA') or plugin_class.METADATA is None:
            raise AttributeError(
                f"{plugin_class.__name__} must define METADATA as a class-level attribute"
            )
        return plugin_class.METADATA

    def discover_plugins(self) -> Dict[str, Type[HUDPlugin]]:
        discovered = {}

        if not self.plugin_dir.exists():
            print(f"Warning: Plugin directory {self.plugin_dir} does not exist")
            return discovered

        plugin_parent = self.plugin_dir.parent.absolute()
        if str(plugin_parent) not in sys.path:
            sys.path.insert(0, str(plugin_parent))

        for plugin_file in self.plugin_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue

            try:
                module_name = f"hud.plugins.{plugin_file.stem}"
                module = importlib.import_module(module_name)

                self.plugin_modules[plugin_file.stem] = module
                self.plugin_file_times[plugin_file.stem] = plugin_file.stat().st_mtime

                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, HUDPlugin) and
                        obj is not HUDPlugin and
                        obj.__module__ == module_name):
                        discovered[name] = obj
                        print(f"Discovered plugin: {name} from {plugin_file.name}")

            except Exception as e:
                print(f"Error loading plugin {plugin_file.name}: {e}")

        self.plugin_classes = discovered
        return discovered

    def check_dependencies(self, plugin_class: Type[HUDPlugin]) -> tuple[bool, List[str]]:
        try:
            metadata = self._get_metadata(plugin_class)
            dependencies = metadata.dependencies

            if not dependencies:
                return True, []

            loaded_plugin_names = {p.metadata.name for p in self.plugins}
            loaded_class_names = {p.__class__.__name__ for p in self.plugins}

            missing = []
            for dep in dependencies:
                if dep not in loaded_plugin_names and dep not in loaded_class_names:
                    missing.append(dep)

            return len(missing) == 0, missing

        except Exception:
            return True, []

    def _get_plugin_dependencies(self, plugin_name: str) -> List[str]:
        if plugin_name not in self.plugin_classes:
            return []

        try:
            metadata = self._get_metadata(self.plugin_classes[plugin_name])
            declared_deps = metadata.dependencies or []

            data_keys_consumed = getattr(metadata, 'consumes', [])

            inferred_deps = []
            for other_name, other_class in self.plugin_classes.items():
                if other_name == plugin_name:
                    continue
                try:
                    other_metadata = self._get_metadata(other_class)
                    provided_keys = other_metadata.provides or []

                    if any(key in provided_keys for key in data_keys_consumed):
                        inferred_deps.append(other_name)
                except Exception:
                    continue

            all_deps = list(set(declared_deps + inferred_deps))
            return all_deps
        except Exception:
            return []

    def topological_sort_plugins(self, plugin_names: List[str]) -> List[str]:
        dependencies = {}
        in_degree = {}

        for name in plugin_names:
            dependencies[name] = self._get_plugin_dependencies(name)
            in_degree[name] = len(dependencies[name])

        queue = [name for name in plugin_names if in_degree[name] == 0]
        sorted_plugins = []

        while queue:
            current = queue.pop(0)
            sorted_plugins.append(current)

            for name in plugin_names:
                if current in dependencies[name]:
                    in_degree[name] -= 1
                    if in_degree[name] == 0:
                        queue.append(name)

        if len(sorted_plugins) != len(plugin_names):
            missing = set(plugin_names) - set(sorted_plugins)
            raise ValueError(f"Circular dependency detected among plugins: {', '.join(missing)}")

        return sorted_plugins

    def load_plugin(self, plugin_class: Type[HUDPlugin],
                   config: Optional[PluginConfig] = None,
                   check_deps: bool = True) -> Optional[HUDPlugin]:
        try:
            if check_deps:
                satisfied, missing = self.check_dependencies(plugin_class)
                if not satisfied:
                    print(f"⚠ Warning: Plugin {plugin_class.__name__} has missing dependencies: {', '.join(missing)}")
                    print(f"  → These plugins must be loaded first. Use topological_sort_plugins() to determine correct load order.")

            if config is None:
                config = PluginConfig()

            plugin = plugin_class(self.context, config)

            if plugin.initialize():
                plugin.initialized = True
                self.plugins.append(plugin)

                if plugin.metadata.provides:
                    provides_str = ', '.join(plugin.metadata.provides)
                    print(f"Loaded plugin: {plugin.metadata.name} v{plugin.metadata.version} [provides: {provides_str}]")
                else:
                    print(f"Loaded plugin: {plugin.metadata.name} v{plugin.metadata.version}")
                return plugin
            else:
                print(f"Failed to initialize plugin: {plugin_class.__name__}")
                return None

        except Exception as e:
            print(f"Error loading plugin {plugin_class.__name__}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def load_plugin_by_name(self, name: str,
                           config: Optional[PluginConfig] = None) -> Optional[HUDPlugin]:
        if name not in self.plugin_classes:
            print(f"Plugin not found: {name}")
            return None

        return self.load_plugin(self.plugin_classes[name], config)

    def unload_plugin(self, plugin: HUDPlugin):
        try:
            plugin.cleanup()
            self.plugins.remove(plugin)
            print(f"Unloaded plugin: {plugin.metadata.name}")
        except Exception as e:
            print(f"Error unloading plugin {plugin.metadata.name}: {e}")

    def update(self):
        current_time = time.time()
        delta_time = current_time - self.last_update_time
        self.last_update_time = current_time

        for plugin in self.plugins:
            if plugin.metadata.enabled:
                try:
                    plugin.update(delta_time)
                except Exception as e:
                    print(f"Error updating plugin {plugin.metadata.name}: {e}")

        for event in self.context.events:
            for plugin in self.plugins:
                if plugin.metadata.enabled:
                    try:
                        plugin.handle_event(event)
                    except Exception as e:
                        print(f"Error handling event in {plugin.metadata.name}: {e}")

        self.context.clear_events()

    def render(self, frame: np.ndarray) -> np.ndarray:
        sorted_plugins = sorted(
            [p for p in self.plugins if p.visible and p.metadata.enabled],
            key=lambda p: p.config.z_index
        )

        for plugin in sorted_plugins:
            try:
                frame = plugin.render(frame)
            except Exception as e:
                print(f"Error rendering plugin {plugin.metadata.name}: {e}")

        return frame

    def handle_key(self, key: int) -> bool:
        handled = False
        for plugin in self.plugins:
            if plugin.metadata.enabled:
                try:
                    if plugin.handle_key(key):
                        handled = True
                except Exception as e:
                    print(f"Error handling key in {plugin.metadata.name}: {e}")
        return handled

    def cleanup(self):
        for plugin in self.plugins[:]:
            self.unload_plugin(plugin)

    def get_plugin(self, name: str) -> Optional[HUDPlugin]:
        for plugin in self.plugins:
            if (plugin.__class__.__name__ == name or
                plugin.metadata.name == name):
                return plugin
        return None

    def list_plugins(self) -> List[Dict[str, Any]]:
        return [{
            'name': p.metadata.name,
            'version': p.metadata.version,
            'author': p.metadata.author,
            'description': p.metadata.description,
            'enabled': p.metadata.enabled,
            'visible': p.visible,
            'z_index': p.config.z_index
        } for p in self.plugins]

    def reload_plugin(self, plugin_name: str) -> bool:
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            print(f"Plugin {plugin_name} not found")
            return False

        saved_config = plugin.config
        saved_visible = plugin.visible

        self.unload_plugin(plugin)

        module_file = None
        for file_name, module in self.plugin_modules.items():
            if hasattr(module, plugin_name):
                module_file = file_name
                break

        if not module_file:
            print(f"Module for {plugin_name} not found")
            return False

        try:
            module_name = f"hud.plugins.{module_file}"
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
                module = sys.modules[module_name]
                self.plugin_modules[module_file] = module

                plugin_path = self.plugin_dir / f"{module_file}.py"
                if plugin_path.exists():
                    self.plugin_file_times[module_file] = plugin_path.stat().st_mtime

            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, HUDPlugin) and
                    obj is not HUDPlugin and
                    name == plugin_name):
                    self.plugin_classes[name] = obj

                    new_plugin = self.load_plugin(obj, saved_config)
                    if new_plugin:
                        new_plugin.visible = saved_visible
                        print(f"✓ Reloaded plugin: {plugin_name}")
                        return True

            print(f"Failed to reload plugin: {plugin_name}")
            return False

        except Exception as e:
            print(f"Error reloading plugin {plugin_name}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def check_for_updates(self) -> List[str]:
        modified = []

        for file_name, last_mtime in self.plugin_file_times.items():
            plugin_path = self.plugin_dir / f"{file_name}.py"
            if plugin_path.exists():
                current_mtime = plugin_path.stat().st_mtime
                if current_mtime > last_mtime:
                    module = self.plugin_modules.get(file_name)
                    if module:
                        for name, obj in inspect.getmembers(module, inspect.isclass):
                            if (issubclass(obj, HUDPlugin) and
                                obj is not HUDPlugin and
                                obj.__module__ == f"hud.plugins.{file_name}"):
                                modified.append(name)

        return modified

    def auto_reload_modified(self) -> int:
        modified = self.check_for_updates()
        reloaded = 0

        for plugin_name in modified:
            if self.reload_plugin(plugin_name):
                reloaded += 1

        return reloaded

    def load_plugin_from_file(self, file_path: str,
                             config: Optional[PluginConfig] = None) -> Optional[HUDPlugin]:
        try:
            plugin_path = Path(file_path)
            if not plugin_path.exists():
                print(f"Plugin file not found: {file_path}")
                return None

            module_name = f"hud.plugins.{plugin_path.stem}"
            spec = importlib.util.spec_from_file_location(module_name, plugin_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                self.plugin_modules[plugin_path.stem] = module
                self.plugin_file_times[plugin_path.stem] = plugin_path.stat().st_mtime

                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, HUDPlugin) and
                        obj is not HUDPlugin and
                        obj.__module__ == module_name):
                        self.plugin_classes[name] = obj

                        plugin = self.load_plugin(obj, config)
                        if plugin:
                            print(f"✓ Dynamically loaded plugin: {name} from {plugin_path.name}")
                            return plugin

            print(f"No valid plugin found in {file_path}")
            return None

        except Exception as e:
            print(f"Error loading plugin from file {file_path}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def enable_plugin(self, plugin_name: str):
        plugin = self.get_plugin(plugin_name)
        if plugin:
            plugin.metadata.enabled = True
            print(f"✓ Enabled plugin: {plugin_name}")
        else:
            print(f"Plugin not found: {plugin_name}")

    def disable_plugin(self, plugin_name: str):
        plugin = self.get_plugin(plugin_name)
        if plugin:
            plugin.metadata.enabled = False
            print(f"✓ Disabled plugin: {plugin_name}")
        else:
            print(f"Plugin not found: {plugin_name}")

    def load_plugins_with_dependencies(self, plugin_configs: List[tuple]) -> List[HUDPlugin]:
        plugin_names = [name for name, _ in plugin_configs]

        try:
            sorted_names = self.topological_sort_plugins(plugin_names)
            print(f"Loading plugins in dependency order: {' → '.join(sorted_names)}")
        except ValueError as e:
            print(f"Error: {e}")
            raise

        config_map = {name: config for name, config in plugin_configs}

        loaded_plugins = []
        for name in sorted_names:
            config = config_map.get(name)
            plugin = self.load_plugin_by_name(name, config)
            if plugin:
                loaded_plugins.append(plugin)

        return loaded_plugins
