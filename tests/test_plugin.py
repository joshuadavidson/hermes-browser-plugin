from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_declares_kernel_browser_provider() -> None:
    manifest = yaml.safe_load((ROOT / "plugin.yaml").read_text())

    assert manifest["name"] == "browser-kernel"
    assert manifest["manifest_version"] == 1
    assert manifest["kind"] == "backend"
    assert manifest["version"] == "0.2.2"
    assert manifest["provides_browser_providers"] == ["kernel"]
    assert manifest["requires_env"] == [
        {
            "name": "KERNEL_API_KEY",
            "description": "Kernel API key",
            "url": "https://dashboard.onkernel.com/api-keys",
            "secret": True,
        }
    ]
    assert manifest["optional_env"] == [
        {
            "name": "KERNEL_PROXY_NAME",
            "description": "Default Kernel proxy name",
            "secret": False,
        },
        {
            "name": "KERNEL_PROFILE_NAME",
            "description": "Default Kernel profile name",
            "secret": False,
        },
    ]


def test_register_adds_kernel_provider() -> None:
    module_name = "browser_kernel_plugin"
    spec = importlib.util.spec_from_file_location(
        module_name,
        ROOT / "__init__.py",
        submodule_search_locations=[str(ROOT)],
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    registered = []

    class Context:
        def register_browser_provider(self, provider) -> None:
            registered.append(provider)

    module.register(Context())

    assert len(registered) == 1
    assert registered[0].name == "kernel"
